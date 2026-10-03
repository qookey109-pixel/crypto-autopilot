from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from scripts.cloud_paper_billing_history_v0_2 import BillingHistoryError
from scripts.cloud_paper_billing_history_v0_3 import collect_report, require_single_run

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def page(number, rows):
    return {"success": True, "result": rows,
            "result_info": {"page": number, "per_page": 100}}


class BillingExecutionV03Tests(unittest.TestCase):
    def test_missing_confirmation_and_rerun_stop_before_network(self):
        for env, reason in (
            ({}, "CONFIRMATION"),
            ({"INPUT_CONFIRM_ONE_TIME_READ_ONLY": "true", "GITHUB_REF": "refs/heads/main",
              "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "2"}, "RERUN"),
        ):
            with self.subTest(reason=reason), patch.dict(os.environ, env, clear=True):
                with patch("urllib.request.build_opener") as network:
                    with self.assertRaisesRegex(BillingHistoryError, reason):
                        require_single_run()
                    network.assert_not_called()

    def test_optional_totals_continue_to_empty_terminal(self):
        calls = []
        def fetch(number, size):
            calls.append((number, size))
            return page(number, [{"id": "private", "amount": 0}] if number == 1 else [])
        report = collect_report(fetch, observed_at=NOW)
        self.assertEqual(calls, [(1, 100), (2, 100)])
        self.assertTrue(report["bounded_traversal_complete"])
        self.assertFalse(report["complete_history_coverage"])
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
        self.assertEqual(report["cloudflare_http_requests_performed"], 2)
        self.assertNotIn("private", str(report))

    def test_failure_retains_prior_redacted_page_and_counts_attempt(self):
        def fetch(number, size):
            if number == 2:
                raise RuntimeError("private response or token")
            return page(number, [{"id": "private", "amount": 0}])
        report = collect_report(fetch, observed_at=NOW)
        self.assertEqual(report["returned_row_count"], 1)
        self.assertEqual(report["cloudflare_http_requests_performed"], 2)
        self.assertEqual(report["reason_code"], "REQUEST_OR_PARSE_FAILED")
        self.assertNotIn("private", str(report))

    def test_page_cap_and_duplicate_stop_without_retry(self):
        report = collect_report(lambda n, s: page(n, [{"id": str(n)}]), observed_at=NOW)
        self.assertEqual(report["cloudflare_http_requests_performed"], 10)
        self.assertFalse(report["bounded_traversal_complete"])
        report = collect_report(lambda n, s: page(n, [{"id": "same"}]), observed_at=NOW)
        self.assertEqual(report["cloudflare_http_requests_performed"], 2)
        self.assertEqual(report["reason_code"], "DUPLICATE_BILLING_HISTORY_ITEM")


if __name__ == "__main__":
    unittest.main()
