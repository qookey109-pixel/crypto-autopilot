from __future__ import annotations

import json
import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from scripts.cloud_paper_billing_history_v0_2 import BillingHistoryError
from scripts.cloud_paper_billing_metadata_diagnostic_v0_5 import (
    diagnose_payload, execute_one_request,
)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def payload(*, page=1, per_page=100, count=1, total_count=1, rows=None):
    return {
        "success": True,
        "errors": [],
        "result": [{}] if rows is None else rows,
        "result_info": {
            "page": page, "per_page": per_page,
            "count": count, "total_count": total_count,
        },
    }


class BillingMetadataDiagnosticV05Tests(unittest.TestCase):
    def test_valid_first_page_reports_only_booleans_and_types(self):
        report = diagnose_payload(payload(), observed_at=NOW)
        self.assertEqual(report["status"], "DIAGNOSTIC_COMPLETE")
        self.assertEqual(report["reason_code"], "FIRST_PAGE_METADATA_VALID")
        self.assertTrue(report["pagination_fields"]["page"]["matches_request"])
        self.assertTrue(report["pagination_fields"]["per_page"]["matches_request"])
        self.assertTrue(report["pagination_fields"]["count"]["matches_result_length"])
        self.assertTrue(report["pagination_fields"]["total_count"]["covers_returned_count"])
        self.assertEqual(report["billing_readiness"], "UNKNOWN")
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
        encoded = json.dumps(report)
        self.assertNotIn('"count": 1', encoded)
        self.assertNotIn('"total_count": 1', encoded)

    def test_reports_exact_mismatched_field_names_without_values(self):
        report = diagnose_payload(
            payload(page=9, per_page=500, count=0, total_count=0, rows=[]),
            observed_at=NOW,
        )
        self.assertEqual(report["reason_code"], "PAGINATION_METADATA_MISMATCH")
        self.assertEqual(report["mismatched_fields"], ["page", "per_page"])
        self.assertNotIn('"9"', json.dumps(report))
        self.assertNotIn('"500"', json.dumps(report))

    def test_count_mismatch_is_identified_without_persisting_row_count(self):
        report = diagnose_payload(payload(count=2, rows=[{}]), observed_at=NOW)
        self.assertIn("count", report["mismatched_fields"])
        self.assertFalse(report["pagination_fields"]["count"]["matches_result_length"])
        self.assertNotIn('"count": 2', json.dumps(report))
        self.assertNotIn('"result_length": 2', json.dumps(report))

    def test_missing_wrong_type_and_bool_metadata_fail_closed(self):
        p = payload(page=True)
        del p["result_info"]["total_count"]
        report = diagnose_payload(p, observed_at=NOW)
        self.assertEqual(report["reason_code"], "PAGINATION_METADATA_INVALID")
        self.assertEqual(report["invalid_fields"], ["page", "total_count"])
        self.assertEqual(report["pagination_fields"]["page"]["json_type"], "boolean")

    def test_failure_bodies_and_rows_never_enter_report(self):
        p = payload(rows=[{"amount": 12345, "id": "private-id"}])
        p["errors"] = [{"message": "private failure detail"}]
        report = diagnose_payload(p, observed_at=NOW)
        encoded = json.dumps(report)
        self.assertEqual(report["reason_code"], "API_ERRORS_PRESENT")
        for secret in ("12345", "private-id", "private failure detail", "amount"):
            self.assertNotIn(secret, encoded)

    def test_execution_has_exactly_one_fetch_after_confirmation_gate(self):
        env = {
            "INPUT_CONFIRM_ONE_TIME_READ_ONLY": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "10",
            "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
            "GITHUB_TOKEN": "gh-token",
            "CLOUDFLARE_ACCOUNT_ID": "account",
            "CLOUDFLARE_BILLING_READONLY_API_TOKEN": "cf-token",
        }
        with patch.dict(os.environ, env, clear=True), patch(
            "scripts.cloud_paper_billing_metadata_diagnostic_v0_5._require_single_dispatch"
        ):
            calls = []
            def fetch(*args):
                calls.append(args)
                return payload()
            report = execute_one_request(fetch_payload=fetch, observed_at=NOW)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["cloudflare_http_requests_performed"], 1)

    def test_failed_attempt_is_counted_and_not_retried(self):
        env = {
            "INPUT_CONFIRM_ONE_TIME_READ_ONLY": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "10",
            "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
            "GITHUB_TOKEN": "gh-token",
            "CLOUDFLARE_ACCOUNT_ID": "account",
            "CLOUDFLARE_BILLING_READONLY_API_TOKEN": "cf-token",
        }
        with patch.dict(os.environ, env, clear=True), patch(
            "scripts.cloud_paper_billing_metadata_diagnostic_v0_5._require_single_dispatch"
        ):
            calls = []
            def fail(*args):
                calls.append(args)
                raise BillingHistoryError("CLOUDFLARE_HTTP_403")
            report = execute_one_request(fetch_payload=fail, observed_at=NOW)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["cloudflare_http_requests_performed"], 1)
        self.assertEqual(report["reason_code"], "CLOUDFLARE_HTTP_403")
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
