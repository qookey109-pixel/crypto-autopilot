from __future__ import annotations

import unittest
from datetime import UTC, datetime

from scripts.cloud_paper_billing_evidence_v0_1 import (
    BillingEvidenceError,
    summarize_subscriptions,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def payload():
    return {
        "success": True,
        "errors": [],
        "result": [
            {
                "id": "subscription-secret-id",
                "price": 0,
                "currency": "USD",
                "rate_plan": {"id": "free", "public_name": "Free"},
                "state": "Provisioned",
            },
            {
                "id": "paid-subscription-id",
                "price": 12.5,
                "currency": "USD",
                "rate_plan": {"id": "pro", "public_name": "Pro"},
                "state": "Paid",
            },
        ],
        "result_info": {"count": 2, "page": 1, "per_page": 20, "total_count": 2},
    }


class CloudPaperBillingEvidenceTests(unittest.TestCase):
    def test_reports_complete_subscription_snapshot_without_ids(self):
        report = summarize_subscriptions(payload(), observed_at=NOW)
        self.assertEqual(report["status"], "READY_FOR_BILLING_REVIEW")
        self.assertEqual(report["subscription_page"]["total_count"], 2)
        self.assertEqual(report["listed_subscription_price_total_usd"], 12.5)
        self.assertEqual(report["zero_cost_conclusion"], "NOT_PROVEN_BY_SUBSCRIPTION_SNAPSHOT")
        encoded = str(report)
        self.assertNotIn("subscription-secret-id", encoded)
        self.assertNotIn("paid-subscription-id", encoded)
        self.assertNotIn("public_name", encoded)
        self.assertFalse(report["account_id_persisted"])
        self.assertFalse(report["raw_response_persisted"])

    def test_rejects_incomplete_or_paginated_result(self):
        value = payload()
        value["result_info"]["total_count"] = 3
        with self.assertRaisesRegex(BillingEvidenceError, "SUBSCRIPTION_PAGE_INCOMPLETE"):
            summarize_subscriptions(value, observed_at=NOW)

    def test_rejects_cloudflare_errors(self):
        value = payload()
        value["errors"] = [{"message": "sensitive provider body"}]
        with self.assertRaisesRegex(BillingEvidenceError, "CLOUDFLARE_RESPONSE_HAS_ERRORS"):
            summarize_subscriptions(value, observed_at=NOW)

    def test_rejects_missing_price(self):
        value = payload()
        del value["result"][0]["price"]
        with self.assertRaisesRegex(BillingEvidenceError, "SUBSCRIPTION_PRICE_MISSING"):
            summarize_subscriptions(value, observed_at=NOW)

    def test_rejects_negative_price(self):
        value = payload()
        value["result"][0]["price"] = -1
        with self.assertRaisesRegex(BillingEvidenceError, "SUBSCRIPTION_PRICE_INVALID"):
            summarize_subscriptions(value, observed_at=NOW)

    def test_rejects_timezone_naive_observation_time(self):
        with self.assertRaisesRegex(BillingEvidenceError, "OBSERVATION_TIMEZONE_MISSING"):
            summarize_subscriptions(payload(), observed_at=datetime(2026, 9, 29, 12, 0))


if __name__ == "__main__":
    unittest.main()
