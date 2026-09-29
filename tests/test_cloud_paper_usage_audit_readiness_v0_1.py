from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts.cloud_paper_usage_audit_readiness_v0_1 import classify_configuration, main


class UsageAuditReadinessTests(unittest.TestCase):
    def test_each_missing_configuration_has_a_distinct_reason(self):
        cases = (
            (False, False, "BLOCKED_MISSING_ACCOUNT_ID_AND_TOKEN"),
            (False, True, "BLOCKED_MISSING_ACCOUNT_ID"),
            (True, False, "BLOCKED_MISSING_READ_ONLY_TOKEN"),
            (True, True, "READY"),
        )
        for account, token, expected in cases:
            with self.subTest(expected=expected):
                report = classify_configuration(account, token)
                self.assertEqual(report["state"], expected)
                self.assertEqual(report["account_id_variable_present"], account)
                self.assertEqual(report["read_only_token_secret_present"], token)
                self.assertEqual(report["cloudflare_requests_performed"], 0)
                self.assertFalse(report["one_time_authority_consumed"])

    def test_runner_entrypoint_never_reads_or_prints_raw_values(self):
        with patch.dict(os.environ, {
            "CF_ACCOUNT_ID_PRESENT": "true",
            "CF_READONLY_TOKEN_PRESENT": "true",
            "CF_ACCOUNT_ID": "account-id-sentinel",
            "CF_READONLY_TOKEN": "secret-token-sentinel",
        }):
            stream = io.StringIO()
            with redirect_stdout(stream):
                main()
        self.assertIn('"state": "READY"', stream.getvalue())
        self.assertNotIn("account-id-sentinel", stream.getvalue())
        self.assertNotIn("secret-token-sentinel", stream.getvalue())

    def test_configured_does_not_claim_api_or_budget_readiness(self):
        report = classify_configuration(True, True)
        self.assertEqual(report["api_permission_state"], "NOT_CHECKED_NO_NETWORK")
        self.assertEqual(report["usage_evidence_state"], "NOT_CHECKED_BY_READINESS")
        self.assertEqual(report["budget_activation_state"], "NOT_AUTHORIZED_BY_READINESS")


if __name__ == "__main__":
    unittest.main()
