"""Synthetic JWK selection; inputs are generated in CI and never fetched."""
import json
import socket
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from crypto_autopilot.paper.synthetic_oidc_v0_1 import select_synthetic_rsa_key


class SyntheticJwksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(RSAAlgorithm.to_jwk(cls.private_key.public_key()))
        cls.jwk.update(kid="synthetic-key", alg="RS256", use="sig")

    def setUp(self):
        for obj, name in ((socket, "getaddrinfo"), (socket.socket, "connect"),
                          (socket.socket, "connect_ex")):
            blocker = patch.object(obj, name, side_effect=AssertionError("network forbidden"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def select(self, keys, kid="synthetic-key"):
        return select_synthetic_rsa_key(json.dumps({"keys": keys}), kid=kid)

    def test_valid_key_and_rotation(self):
        other = dict(self.jwk, kid="other")
        result = self.select([other, self.jwk])
        self.assertEqual(result.public_numbers(), self.private_key.public_key().public_numbers())

    def test_missing_duplicate_and_wrong_use_are_rejected(self):
        self.assertIsNone(self.select([], kid="missing"))
        self.assertIsNone(self.select([self.jwk, self.jwk]))
        for changes in ({"alg": "HS256"}, {"use": "enc"}, {"kty": "EC"},
                        {"x5u": "https://invalid"}, {"d": "private"}):
            with self.subTest(changes=changes):
                self.assertIsNone(self.select([self.jwk | changes]))

    def test_malformed_and_excessive_input_rejected(self):
        for value in ("", "{}", '{"keys":[],"keys":[]}', "x" * 50000):
            with self.subTest(size=len(value)):
                self.assertIsNone(select_synthetic_rsa_key(value, kid="synthetic-key"))
        self.assertIsNone(self.select([dict(self.jwk, kid=str(i)) for i in range(33)]))


if __name__ == "__main__":
    unittest.main()
