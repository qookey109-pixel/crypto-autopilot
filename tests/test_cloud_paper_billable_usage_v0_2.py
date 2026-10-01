from __future__ import annotations

import unittest
from datetime import UTC, date, datetime

from scripts.cloud_paper_billable_usage_v0_2 import UsageError, summarize_usage

OBSERVED = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
START = date(2026, 10, 1)
END = date(2026, 10, 1)


def payload():
    return {
        "success": True,
        "errors": [],
        "result": [{
            "ChargePeriodStart": "2026-10-01T00:00:00Z",
            "ChargePeriodEnd": "2026-10-02T00:00:00Z",
            "ConsumedQuantity": 10,
            "ConsumedUnit": "Requests",
            "x_BillableMetricId": "workers_requests",
            "BilledCost": 0,
            "BillingCurrency": "USD",
            "BillingAccountId": "private-account-id",
            "BillingAccountName": "private-account-name",
            "ChargeDescription": "sensitive description",
        }],
    }


class CloudPaperBillableUsageTests(unittest.TestCase):
    def test_valid_rows_are_review_only_and_account_identity_is_redacted(self):
        report = summarize_usage(payload(), observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["status"], "READY_FOR_REVIEW")
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
        self.assertEqual(report["reported_cost_total"], 0)
        self.assertEqual(report["reported_cost_currency"], "USD")
        encoded = str(report)
        for private in ("private-account-id", "private-account-name", "sensitive description"):
            self.assertNotIn(private, encoded)
        self.assertFalse(report["account_id_persisted"])
        self.assertEqual(report["cloud_paper_activation"], "REMAINS_DISABLED")

    def test_missing_cost_fields_stay_unknown(self):
        value = payload()
        del value["result"][0]["BilledCost"]
        report = summarize_usage(value, observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["status"], "READY_FOR_REVIEW")
        self.assertFalse(report["cost_fields_present_for_all_rows"])
        self.assertIsNone(report["reported_cost_total"])
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")

    def test_empty_response_is_not_zero(self):
        value = payload()
        value["result"] = []
        report = summarize_usage(value, observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["reason_code"], "EMPTY_USAGE_RESPONSE_NOT_ZERO")
        self.assertIsNone(report["reported_cost_total"])

    def test_failed_response_stays_review_required(self):
        report = summarize_usage(
            {"success": False, "errors": [{"message": "secret response text"}]},
            observed_at=OBSERVED, window_start=START, window_end=END,
        )
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["reason_code"], "CLOUDFLARE_RESPONSE_UNSUCCESSFUL")
        self.assertNotIn("secret response text", str(report))

    def test_invalid_metric_and_numeric_fields_fail_closed(self):
        value = payload()
        value["result"][0]["ConsumedQuantity"] = -1
        report = summarize_usage(value, observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["reason_code"], "CONSUMED_QUANTITY_INVALID")
        value = payload()
        value["result"][0]["x_BillableMetricId"] = ""
        report = summarize_usage(value, observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["reason_code"], "BILLABLE_METRIC_ID_INVALID")

    def test_query_window_and_timezone_are_validated(self):
        report = summarize_usage(
            payload(), observed_at=OBSERVED,
            window_start=date(2026, 8, 1), window_end=date(2026, 10, 1),
        )
        self.assertEqual(report["reason_code"], "QUERY_WINDOW_INVALID")
        with self.assertRaisesRegex(UsageError, "OBSERVATION_TIMEZONE_MISSING"):
            summarize_usage(
                payload(), observed_at=datetime(2026, 10, 1),
                window_start=START, window_end=END,
            )

    def test_rows_outside_requested_range_are_rejected(self):
        value = payload()
        value["result"][0]["ChargePeriodStart"] = "2026-09-30T00:00:00Z"
        report = summarize_usage(value, observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["reason_code"], "CHARGE_PERIOD_OUTSIDE_QUERY_WINDOW")

    def test_mixed_currency_costs_do_not_get_summed(self):
        value = payload()
        second = dict(value["result"][0])
        second["BillingCurrency"] = "EUR"
        value["result"].append(second)
        report = summarize_usage(value, observed_at=OBSERVED, window_start=START, window_end=END)
        self.assertEqual(report["reason_code"], "MIXED_BILLING_CURRENCIES")
        self.assertIsNone(report["reported_cost_total"])


if __name__ == "__main__":
    unittest.main()
