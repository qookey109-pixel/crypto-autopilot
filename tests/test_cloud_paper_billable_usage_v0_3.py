from __future__ import annotations

import unittest
from datetime import UTC, datetime

from scripts.cloud_paper_billable_usage_v0_3 import UsageError, summarize_usage

OBSERVED = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)


def payload():
    return {
        "success": True,
        "errors": [],
        "result": [{
            "BillingPeriodStart": "2026-09-14T00:00:00Z",
            "ChargePeriodStart": "2026-10-01T00:00:00Z",
            "ChargePeriodEnd": "2026-10-02T00:00:00Z",
            "ServiceName": "Workers Standard",
            "ServiceFamilyName": "Workers",
            "ConsumedQuantity": 10,
            "ConsumedUnit": "Requests",
            "BilledCost": 0,
            "BillingCurrency": "USD",
            "BillingAccountId": "private-account-id",
            "BillingAccountName": "private-account-name",
            "ZoneId": "private-zone-id",
            "ZoneName": "private.example",
            "ChargeDescription": "private detail",
        }],
    }


class CloudPaperBillableUsageV03Tests(unittest.TestCase):
    def test_valid_rows_redact_identity_and_never_prove_zero_cost(self):
        report = summarize_usage(payload(), observed_at=OBSERVED)
        self.assertEqual(report["status"], "READY_FOR_REVIEW")
        self.assertEqual(report["reason_code"], "USAGE_ROWS_CAPTURED_REVIEW_REQUIRED_FOR_SCOPE")
        self.assertEqual(report["reported_billed_cost_total"], 0)
        self.assertEqual(report["reported_billing_currency"], "USD")
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
        self.assertFalse(report["fixed_subscription_charges_included"])
        self.assertEqual(report["cloud_paper_activation"], "REMAINS_DISABLED")
        for private in ("private-account-id", "private-account-name", "private-zone-id",
                        "private.example", "private detail"):
            self.assertNotIn(private, str(report))

    def test_missing_cost_fields_stay_unknown(self):
        value = payload()
        del value["result"][0]["BilledCost"]
        report = summarize_usage(value, observed_at=OBSERVED)
        self.assertEqual(report["status"], "READY_FOR_REVIEW")
        self.assertFalse(report["all_rows_have_billed_cost"])
        self.assertIsNone(report["reported_billed_cost_total"])
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")

    def test_empty_rows_are_not_zero(self):
        value = payload()
        value["result"] = []
        report = summarize_usage(value, observed_at=OBSERVED)
        self.assertEqual(report["reason_code"], "EMPTY_USAGE_RESPONSE_NOT_ZERO")
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_invalid_period_or_quantity_fails_closed(self):
        value = payload()
        value["result"][0]["ChargePeriodEnd"] = value["result"][0]["ChargePeriodStart"]
        self.assertEqual(summarize_usage(value, observed_at=OBSERVED)["reason_code"],
                         "BILLING_PERIOD_INVALID")
        value = payload()
        value["result"][0]["ConsumedQuantity"] = -1
        self.assertEqual(summarize_usage(value, observed_at=OBSERVED)["reason_code"],
                         "CONSUMED_QUANTITY_INVALID")

    def test_multiple_currencies_are_not_summed(self):
        value = payload()
        second = dict(value["result"][0])
        second["BillingCurrency"] = "EUR"
        value["result"].append(second)
        report = summarize_usage(value, observed_at=OBSERVED)
        self.assertEqual(report["reason_code"], "MIXED_BILLING_CURRENCIES")
        self.assertIsNone(report["reported_billed_cost_total"])

    def test_timezone_is_required(self):
        with self.assertRaisesRegex(UsageError, "OBSERVATION_TIMEZONE_MISSING"):
            summarize_usage(payload(), observed_at=datetime(2026, 10, 1, 10, 0))


if __name__ == "__main__":
    unittest.main()
