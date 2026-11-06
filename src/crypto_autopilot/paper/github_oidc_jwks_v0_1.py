"""Bounded fixed-issuer key retrieval; not a production authorization boundary.

This component is dormant by default. A verified key proves only signature
origin; a separately protected broker, approved policy, replay protection and
bounded account-wide admission are still required before any production use.
"""
import json
from urllib.request import HTTPRedirectHandler, Request, build_opener

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

_GITHUB_JWKS_URL = "https://token.actions.githubusercontent.com/.well-known/jwks"
_MAX_BODY = 65536


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_github_signing_key(kid, *, execution_authorized=False):
    """Fetch at most once from the fixed HTTPS issuer. Never logs tokens or bodies.

    A successful return does not authenticate a job, prevent replay, establish
    account headroom, or authorize a workflow or storage operation.
    """
    if execution_authorized is not True:
        return None
    if not isinstance(kid, str) or not kid or len(kid) > 256:
        return None
    try:
        request = Request(_GITHUB_JWKS_URL, method="GET", headers={"Accept": "application/json"})
        with build_opener(_NoRedirect()).open(request, timeout=10) as response:
            if response.status != 200:
                return None
            raw = response.read(_MAX_BODY + 1)
        if len(raw) > _MAX_BODY:
            return None
        document = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            return None
        keys = document["keys"]
        if not 1 <= len(keys) <= 32:
            return None
        identifiers = [item.get("kid") if isinstance(item, dict) else None for item in keys]
        if (any(not isinstance(value, str) or not value or len(value) > 256
                for value in identifiers)
                or len(set(identifiers)) != len(identifiers) or kid not in identifiers):
            return None
        item = keys[identifiers.index(kid)]
        if (item.get("kty") != "RSA" or item.get("alg") != "RS256"
                or item.get("use") != "sig" or "x5u" in item
                or item.get("key_ops", ["verify"]) != ["verify"]):
            return None
        key = jwt.PyJWK.from_dict(item, algorithm="RS256").key
        if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
            return None
        return key
    except Exception:
        # Unavailable key material blocks the caller; exceptions can contain URLs
        # or response details, so no raw exception is persisted or emitted.
        return None
