"""Bounded GitHub JWKS transport contract tests; no external calls."""
import json
import socket
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

try:
    from crypto_autopilot.paper.github_oidc_jwks_v0_1 import load_github_signing_key
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.github_oidc_jwks_v0_1":
        raise
    load_github_signing_key = None


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.body[:limit]


class GithubJwksTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(load_github_signing_key, "bounded JWKS loader not implemented")
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(RSAAlgorithm.to_jwk(self.key.public_key()))
        jwk.update(kid="test-key", alg="RS256", use="sig", x5c=["ignored-certificate"])
        self.body = json.dumps({"keys": [jwk]}).encode()
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_disabled_never_constructs_network_client(self):
        with patch("crypto_autopilot.paper.github_oidc_jwks_v0_1.build_opener") as opener:
            self.assertIsNone(load_github_signing_key("test-key"))
            opener.assert_not_called()

    def test_authorized_fixed_host_one_get_selects_rsa_key(self):
        with patch("crypto_autopilot.paper.github_oidc_jwks_v0_1.build_opener") as opener:
            opener.return_value.open.return_value = FakeResponse(self.body)
            selected = load_github_signing_key("test-key", execution_authorized=True)
            self.assertEqual(selected.public_numbers(), self.key.public_key().public_numbers())
            self.assertEqual(opener.return_value.open.call_count, 1)
            args, kwargs = opener.return_value.open.call_args
            self.assertEqual(args[0].full_url, "https://token.actions.githubusercontent.com/.well-known/jwks")
            self.assertEqual(args[0].get_method(), "GET")
            self.assertEqual(kwargs["timeout"], 10)

    def test_bad_response_and_unknown_key_fail_closed(self):
        cases = [
            b"x" * 65537,
            b'{"keys":[]}',
            b'{"keys":[], "keys":[]}',
            self.body,
        ]
        for body in cases:
            with self.subTest(size=len(body)), patch(
                "crypto_autopilot.paper.github_oidc_jwks_v0_1.build_opener"
            ) as opener:
                opener.return_value.open.return_value = FakeResponse(body)
                self.assertIsNone(load_github_signing_key("unknown", execution_authorized=True))
                self.assertEqual(opener.return_value.open.call_count, 1)

    def test_bad_kid_or_failed_request_never_retries(self):
        for kid in ("", "x" * 257, None):
            with self.subTest(kid=kid), patch(
                "crypto_autopilot.paper.github_oidc_jwks_v0_1.build_opener"
            ) as opener:
                self.assertIsNone(load_github_signing_key(kid, execution_authorized=True))
                opener.assert_not_called()
        with patch("crypto_autopilot.paper.github_oidc_jwks_v0_1.build_opener") as opener:
            opener.return_value.open.side_effect = TimeoutError()
            self.assertIsNone(load_github_signing_key("test-key", execution_authorized=True))
            self.assertEqual(opener.return_value.open.call_count, 1)
