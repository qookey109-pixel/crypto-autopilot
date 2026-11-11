"""GitHub-signed job claims, prepared only; not a production admission boundary.

The caller must obtain policy and time from an independently trusted boundary.
A signed bearer may be stolen or raced. This verifier alone never authorizes a
ticket, claims replay protection, or performs any D1/R2/provider operation.
"""
import re
from dataclasses import dataclass

import jwt

from crypto_autopilot.paper.github_oidc_jwks_v0_1 import load_github_signing_key
from crypto_autopilot.paper.synthetic_oidc_v0_1 import _decode_object

_ISSUER = "https://token.actions.githubusercontent.com"
_POLICY_FIELDS = frozenset({
    "aud", "sub", "repository", "repository_id", "ref",
    "workflow_ref", "sha", "workflow_sha",
})
_SHA = re.compile(r"[0-9a-f]{40}")
_ID = re.compile(r"[1-9][0-9]{0,19}")


@dataclass(frozen=True, slots=True)
class SignedJobClaims:
    run_id: int
    check_run_id: int
    run_attempt: int


def _valid_policy(policy):
    if not isinstance(policy, dict) or set(policy) != _POLICY_FIELDS:
        return False
    if any(not isinstance(v, str) or not v or len(v) > 512 for v in policy.values()):
        return False
    repo = policy["repository"]
    return (
        re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) is not None
        and _ID.fullmatch(policy["repository_id"]) is not None
        and policy["ref"] == "refs/heads/main"
        and policy["sub"] == f"repo:{repo}:ref:refs/heads/main"
        and policy["workflow_ref"].startswith(f"{repo}/.github/workflows/")
        and policy["workflow_ref"].endswith("@refs/heads/main")
        and _SHA.fullmatch(policy["sha"]) is not None
        and _SHA.fullmatch(policy["workflow_sha"]) is not None
    )


def verify_github_job(token, *, policy, now, execution_authorized=False):
    """Validate claims against supplied static policy and return signed IDs.

    This is a prepared primitive, not an identity or replay boundary: policy and
    clock are caller-provided, and a stolen valid JWT can win a race.
    """
    if execution_authorized is not True:
        return None
    if (not _valid_policy(policy) or type(now) is not int or now <= 0
            or not isinstance(token, str) or len(token) > 16384):
        return None
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, unverified = _decode_object(parts[0]), _decode_object(parts[1])
        kid = header.get("kid")
        if (set(header) - {"alg", "kid", "typ"} or header.get("alg") != "RS256"
                or header.get("typ", "JWT") != "JWT"
                or not isinstance(kid, str) or not kid or len(kid) > 256):
            return None
        for name in ("iat", "nbf", "exp"):
            if type(unverified.get(name)) is not int:
                return None
        for name in ("run_id", "check_run_id"):
            if (not isinstance(unverified.get(name), str)
                    or not _ID.fullmatch(unverified[name])):
                return None
        if (unverified.get("run_attempt") != "1"
                or unverified.get("event_name") not in ("schedule", "workflow_dispatch")
                or unverified.get("runner_environment") != "github-hosted"
                or unverified.get("ref_type") != "branch"
                or any(unverified.get(k) != v for k, v in policy.items())
                or not isinstance(unverified.get("jti"), str)
                or not unverified["jti"] or len(unverified["jti"]) > 256):
            return None
        iat, nbf, exp = (unverified[k] for k in ("iat", "nbf", "exp"))
        if not (iat <= now and nbf <= now < exp and iat < exp
                and nbf < exp and exp - iat <= 600):
            return None
        key = load_github_signing_key(kid, execution_authorized=True)
        if key is None:
            return None
        claims = jwt.decode(
            token, key, algorithms=["RS256"], issuer=_ISSUER, audience=policy["aud"],
            options={
                "require": ["iss", "aud", "sub", "iat", "nbf", "exp", "jti",
                            *_POLICY_FIELDS, "run_id", "check_run_id", "run_attempt",
                            "event_name", "runner_environment", "ref_type"],
                "verify_iat": False, "verify_nbf": False, "verify_exp": False,
                "strict_aud": True,
            },
        )
        if claims != unverified:
            return None
        return SignedJobClaims(
            run_id=int(claims["run_id"]), check_run_id=int(claims["check_run_id"]),
            run_attempt=1,
        )
    except (ValueError, TypeError, UnicodeError, OverflowError, jwt.PyJWTError):
        return None
