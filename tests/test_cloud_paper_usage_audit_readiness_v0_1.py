from __future__ import annotations

import unittest

from scripts.cloud_paper_usage_audit_readiness_v0_1 import classify_configuration


class UsageAuditReadinessTests(unittest.TestCase):
    def test_each_missing_configuration_has_a_distinct_reason(self):
        cases = (
            (None, None, "BLOCKED_MISSING_ACCOUNT_ID_AND_TOKEN"),
            (None, "secret-token-sentinel", "BLOCKED_MISSING_ACCOUNT_ID"),
            ("account-id-sentinel", None, "BLOCKED_MISSING_READ_ONLY_TOKEN"),
            ("account-id-sentinel", "secret-token-sentinel", "READY"),
        )
        for account, token, expected in cases:
            with self.subTest(expected=expected):
                report = classify_configuration(account, token)
                self.assertEqual(report["state"], expected)
                self.assertEqual(report["account_id_variable_present"], bool(account))
                self.assertEqual(report["read_only_token_secret_present"], bool(token))
                self.assertEqual(report["cloudflare_requests_performed"], 0)
                self.assertFalse(report["one_time_authority_consumed"])
                self.assertNotIn("account-id-sentinel", str(report))
                self.assertNotIn("secret-token-sentinel", str(report))

    def test_configured_does_not_claim_api_or_budget_readiness(self):
        report = classify_configuration("account", "token")
        self.assertEqual(report["api_permission_state"], "NOT_CHECKED_NO_NETWORK")
        self.assertEqual(report["usage_evidence_state"], "NOT_CHECKED_BY_READINESS")
        self.assertEqual(report["budget_activation_state"], "NOT_AUTHORIZED_BY_READINESS")


if __name__ == "__main__":
    unittest.main()
