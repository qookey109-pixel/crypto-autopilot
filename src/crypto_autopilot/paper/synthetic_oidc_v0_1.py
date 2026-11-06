"""Offline synthetic OIDC experiment; NOT an authorization boundary.

No trusted key discovery, job ownership or replay protection exists here. This
module must not be connected to runtime admission or used with real tokens.
"""

import base64
import json

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

_ISSUER = "https://token.actions.githubusercontent.com"
_FIELDS = (
    "aud", "sub", "ref_type", "runner_environment", "repository_id",
    "repository", "ref", "sha", "workflow_ref",
    "workflow_sha", "event_name", "run_id", "run_attempt", "check_run_id",
)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _decode_object(segment):
    raw = base64.b64decode(
        segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True
    )
    value = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value


def select_synthetic_rsa_key(document, *, kid):
    """Select only from synthetic input; origin and key trust are NOT verified."""
    try:
        if (not isinstance(document, str) or len(document) > 32768
                or not isinstance(kid, str) or not kid or len(kid) > 256):
            return None
        body = json.loads(document, object_pairs_hook=_unique_object)
        if not isinstance(body, dict) or set(body) != {"keys"}:
            return None
        keys = body["keys"]
        if not isinstance(keys, list) or not 1 <= len(keys) <= 32:
            return None
        identifiers = [key.get("kid") if isinstance(key, dict) else None for key in keys]
        if (any(not isinstance(value, str) or not value or len(value) > 256
                for value in identifiers)
                or len(set(identifiers)) != len(identifiers) or kid not in identifiers):
            return None
        item = keys[identifiers.index(kid)]
        required = {"kty", "kid", "alg", "use", "n", "e"}
        if (not required <= set(item) or set(item) - required - {"key_ops"}
                or item.get("key_ops", ["verify"]) != ["verify"]
                or item["kty"] != "RSA" or item["alg"] != "RS256"
                or item["use"] != "sig"):
            return None
        key = jwt.PyJWK.from_dict(item, algorithm="RS256").key
        if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
            return None
        return key
    except (ValueError, TypeError, KeyError, UnicodeError, jwt.PyJWTError, OverflowError):
        return None


def verify_synthetic_oidc(token, public_key, *, expected, expected_kid, now):
    """Verify only synthetic fixtures against caller-provided synthetic inputs.

    A True result is NOT evidence of a trusted key or of current-job ownership.
    """
    try:
        if (
            not isinstance(token, str)
            or len(token) > 16384
            or not isinstance(public_key, rsa.RSAPublicKey)
            or public_key.key_size < 2048
            or type(now) is not int
            or not isinstance(expected, dict)
            or set(expected) != set(_FIELDS)
            or any(not isinstance(expected[k], str) or not expected[k] for k in _FIELDS)
            or not isinstance(expected_kid, str)
            or not expected_kid
        ):
            return False
        parts = token.split(".")
        if len(parts) != 3:
            return False
        header, unverified = _decode_object(parts[0]), _decode_object(parts[1])
        if (
            set(header) - {"alg", "kid", "typ"}
            or header.get("alg") != "RS256"
            or header.get("kid") != expected_kid
            or header.get("typ", "JWT") != "JWT"
        ):
            return False
        if any(type(unverified.get(k)) is not int for k in ("iat", "nbf", "exp")):
            return False
        claims = jwt.decode(
            token, public_key, algorithms=["RS256"], issuer=_ISSUER,
            audience=expected["aud"],
            options={
                "require": ["iss", "aud", "iat", "nbf", "exp", "jti", *_FIELDS],
                "verify_iat": False, "verify_nbf": False, "verify_exp": False,
                "strict_aud": True,
            },
        )
        if claims != unverified:
            return False
        if any(type(claims.get(k)) is not str or claims[k] != expected[k] for k in _FIELDS):
            return False
        jti = claims.get("jti")
        iat, nbf, exp = (claims[k] for k in ("iat", "nbf", "exp"))
        return (
            isinstance(jti, str)
            and bool(jti)
            and iat <= now
            and nbf <= now
            and iat < exp
            and nbf < exp
            and now < exp
            and exp - iat <= 600
        )
    except (ValueError, TypeError, UnicodeError, jwt.PyJWTError, OverflowError):
        return False
