"""Synthetic-only OIDC verification tests. No GitHub token or network is used."""

import json
import socket
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from crypto_autopilot.paper.synthetic_oidc_v0_1 import verify_synthetic_oidc


class SyntheticOidcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.blockers = [
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("network forbidden")),
            patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")),
            patch.object(socket.socket, "connect_ex", side_effect=AssertionError("network forbidden")),
        ]
        for blocker in self.blockers:
            blocker.start()
            self.addCleanup(blocker.stop)
        self.claims = {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "synthetic-paper-test",
            "sub": "repo:example/repo:ref:refs/heads/main",
            "ref_type": "branch",
            "runner_environment": "github-hosted",
            "repository_id": "123",
            "repository": "example/repo",
            "ref": "refs/heads/main",
            "sha": "a" * 40,
            "workflow_ref": "example/repo/.github/workflows/paper.yml@refs/heads/main",
            "workflow_sha": "a" * 40,
            "event_name": "workflow_dispatch",
            "run_id": "456",
            "run_attempt": "1",
            "check_run_id": "789",
            "jti": "synthetic-jti",
            "iat": 1000,
            "nbf": 1000,
            "exp": 1300,
        }
        self.expected = {k: self.claims[k] for k in (
            "aud", "sub", "ref_type", "runner_environment", "repository_id", "repository", "ref", "sha",
            "workflow_ref", "workflow_sha", "event_name", "run_id",
            "run_attempt", "check_run_id",
        )}

    def verify(self, claims=None, key=None, headers=None, now=1100):
        token = jwt.encode(
            claims if claims is not None else self.claims,
            key or self.key,
            algorithm="RS256",
            headers=headers or {"kid": "synthetic-key"},
        )
        return verify_synthetic_oidc(
            token, self.key.public_key(), expected=self.expected,
            expected_kid="synthetic-key", now=now,
        )

    def test_valid_synthetic_signature_and_claims(self):
        self.assertTrue(self.verify())

    def test_mismatched_bound_claims_rejected(self):
        for field in self.expected:
            with self.subTest(field=field):
                claims = dict(self.claims, **{field: "forged"})
                self.assertFalse(self.verify(claims))

    def test_untrusted_key_and_header_rejected(self):
        self.assertFalse(self.verify(key=self.other_key))
        for headers in (
            {"kid": "wrong"}, {"kid": "synthetic-key", "jku": "https://invalid"},
            {"kid": "synthetic-key", "x5u": "https://invalid"},
            {"kid": "synthetic-key", "crit": ["test"], "test": "value"},
        ):
            with self.subTest(headers=headers):
                self.assertFalse(self.verify(headers=headers))

    def test_invalid_lifetimes_and_identity_rejected(self):
        for changes in (
            {"iss": "https://example.invalid"},
            {"jti": ""},
            {"iat": True}, {"nbf": "1000"}, {"exp": 1099},
            {"iat": 1101}, {"nbf": 1101},
            {"iat": 1000, "exp": 1601},
            {"iat": 1100, "exp": 1100},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(self.verify(dict(self.claims, **changes)))

    def test_signed_duplicate_claims_are_rejected(self):
        original = json.dumps(self.claims, separators=(",", ":"))
        for duplicate in ('"sub":"forged"', '"aud":"forged"', '"exp":9999'):
            payload = (original[:-1] + "," + duplicate + "}").encode()
            token = jwt.api_jws.encode(
                payload, self.key, algorithm="RS256", headers={"kid": "synthetic-key"},
            )
            with self.subTest(duplicate=duplicate):
                self.assertFalse(verify_synthetic_oidc(
                    token, self.key.public_key(), expected=self.expected,
                    expected_kid="synthetic-key", now=1100,
                ))

    def test_missing_claims_and_unexpected_audience_are_rejected(self):
        for name in self.expected:
            claims = self.claims.copy()
            del claims[name]
            with self.subTest(missing=name):
                self.assertFalse(self.verify(claims))
        self.assertFalse(self.verify(dict(self.claims, aud=["synthetic-paper-test", "other"])))

    def test_invalid_input_returns_false_without_token_contents(self):
        for token in ("", "not.a.jwt", "x" * 20000):
            with self.subTest(length=len(token)):
                self.assertFalse(verify_synthetic_oidc(
                    token, self.key.public_key(), expected=self.expected,
                    expected_kid="synthetic-key", now=1100,
                ))


if __name__ == "__main__":
    unittest.main()
