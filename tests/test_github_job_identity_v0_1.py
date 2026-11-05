"""Signed job-claim validation tests using generated keys; network is forbidden."""
import json
import socket
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

try:
    from crypto_autopilot.paper.github_job_identity_v0_1 import verify_github_job
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.github_job_identity_v0_1":
        raise
    verify_github_job = None


class GitHubJobIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.assertIsNotNone(verify_github_job, "signed claim verifier not implemented")
        blocker = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        blocker.start()
        self.addCleanup(blocker.stop)
        self.policy = {
            "aud": "example-paper-gateway",
            "sub": "repo:example/repo:ref:refs/heads/main",
            "repository": "example/repo",
            "repository_id": "123",
            "ref": "refs/heads/main",
            "workflow_ref": "example/repo/.github/workflows/paper.yml@refs/heads/main",
            "sha": "a" * 40,
            "workflow_sha": "a" * 40,
        }
        self.claims = {
            **self.policy, "iss": "https://token.actions.githubusercontent.com",
            "ref_type": "branch", "runner_environment": "github-hosted",
            "event_name": "workflow_dispatch", "run_id": "456",
            "run_attempt": "1", "check_run_id": "789",
            "iat": 1000, "nbf": 1000, "exp": 1300, "jti": "one-token-id",
        }

    def token(self, changes=None, key=None, headers=None):
        return jwt.encode({**self.claims, **(changes or {})}, key or self.key,
                          algorithm="RS256", headers=headers or {"kid": "test-key"})

    def verify(self, token, **kwargs):
        return verify_github_job(token, policy=self.policy, now=1100, **kwargs)

    def test_disabled_does_not_fetch_key(self):
        with patch("crypto_autopilot.paper.github_job_identity_v0_1.load_github_signing_key") as loader:
            self.assertIsNone(self.verify(self.token()))
            loader.assert_not_called()

    def test_returns_signed_job_identifiers_not_caller_supplied_values(self):
        with patch("crypto_autopilot.paper.github_job_identity_v0_1.load_github_signing_key",
                   return_value=self.key.public_key()):
            identity = self.verify(self.token(), execution_authorized=True)
            self.assertEqual((identity.run_id, identity.check_run_id, identity.run_attempt),
                             (456, 789, 1))
            other = self.verify(self.token({"run_id": "457", "check_run_id": "790"}),
                                execution_authorized=True)
            self.assertEqual((other.run_id, other.check_run_id), (457, 790))

    def test_untrusted_signature_and_claims_are_rejected(self):
        changes = [
            {"repository_id": "999"}, {"sub": "repo:other"},
            {"ref": "refs/heads/not-main"}, {"workflow_ref": "other"},
            {"workflow_sha": "b" * 40}, {"sha": "b" * 40},
            {"runner_environment": "self-hosted"}, {"ref_type": "tag"},
            {"event_name": "pull_request"}, {"run_attempt": "2"},
            {"run_id": "0001"}, {"check_run_id": "0"},
            {"iat": True}, {"exp": 1100}, {"nbf": 1101}, {"jti": ""},
        ]
        with patch("crypto_autopilot.paper.github_job_identity_v0_1.load_github_signing_key",
                   return_value=self.key.public_key()):
            self.assertIsNone(self.verify(self.token(key=self.wrong_key), execution_authorized=True))
            for change in changes:
                with self.subTest(change=change):
                    self.assertIsNone(self.verify(self.token(change), execution_authorized=True))

    def test_missing_or_duplicated_claims_and_remote_key_headers_rejected(self):
        payload = json.dumps(self.claims, separators=(",", ":"))
        duplicate = jwt.api_jws.encode((payload[:-1] + ',"run_id":"999"}').encode(),
                                       self.key, algorithm="RS256", headers={"kid": "test-key"})
        missing = dict(self.claims)
        del missing["check_run_id"]
        with patch("crypto_autopilot.paper.github_job_identity_v0_1.load_github_signing_key",
                   return_value=self.key.public_key()) as loader:
            for token in (
                duplicate,
                jwt.encode(missing, self.key, algorithm="RS256", headers={"kid": "test-key"}),
                self.token(headers={"kid": "test-key", "jku": "https://invalid"}),
            ):
                self.assertIsNone(self.verify(token, execution_authorized=True))
            self.assertLessEqual(loader.call_count, 1)

    def test_bad_static_policy_stops_before_key_fetch(self):
        with patch("crypto_autopilot.paper.github_job_identity_v0_1.load_github_signing_key") as loader:
            for bad in ({}, {**self.policy, "run_id": "456"},
                        {**self.policy, "sha": "not-a-sha"}):
                with self.subTest(bad=bad):
                    self.assertIsNone(verify_github_job(
                        self.token(), policy=bad, now=1100, execution_authorized=True))
            loader.assert_not_called()
