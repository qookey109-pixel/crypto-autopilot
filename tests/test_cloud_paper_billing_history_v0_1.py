from __future__ import annotations

import unittest
from datetime import UTC, datetime

from scripts.cloud_paper_billing_history_v0_1 import BillingHistoryError, summarize_pages

NOW = datetime(2026, 10, 2, 1, 0, tzinfo=UTC)


def page(number: int, rows: list[dict], *, total: int, per_page: int = 2):
    return {
        "success": True,
        "errors": [],
        "result": rows,
        "result_info": {
            "count": len(rows), "page": number, "per_page": per_page,
            "total_count": total,
        },
    }


def row(item_id: str, *, amount=0, amount_to_pay=0):
    return {
        "id": item_id,
        "action": "subscription",
        "type": "charge",
        "status": "paid",
        "currency": "USD",
        "amount": amount,
        "amount_to_pay": amount_to_pay,
        "occurred_at": "2026-10-01T12:00:00Z",
        "description": "must not persist",
        "hosted_invoice_url": "https://secret.example/invoice",
        "invoice_id": "private-invoice-id",
    }


class BillingHistoryTests(unittest.TestCase):
    def test_complete_pages_redact_identifiers_and_keep_zero_unknown(self):
        report = summarize_pages(
            [page(1, [row("id-1"), row("id-2")], total=3),
             page(2, [row("id-3", amount=12.5, amount_to_pay=3)], total=3)],
            observed_at=NOW,
        )
        self.assertEqual(report["status"], "READY_FOR_BILLING_REVIEW")
        self.assertTrue(report["complete_history_coverage"])
        self.assertEqual(report["returned_row_count"], 3)
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
        self.assertEqual(report["items"][2]["amount"], 12.5)
        encoded = str(report)
        for private in ("id-1", "private-invoice-id", "secret.example", "must not persist"):
            self.assertNotIn(private, encoded)

    def test_truncated_pages_and_item_cap_are_review_required(self):
        report = summarize_pages(
            [page(1, [row("id-1"), row("id-2")], total=5)],
            observed_at=NOW, max_items=2,
        )
        self.assertEqual(report["reason_code"], "BILLING_HISTORY_ITEM_CAP_EXCEEDED")
        self.assertFalse(report["complete_history_coverage"])

    def test_duplicate_ids_fail_closed(self):
        report = summarize_pages(
            [page(1, [row("same"), row("same")], total=2)],
            observed_at=NOW,
        )
        self.assertEqual(report["reason_code"], "DUPLICATE_BILLING_HISTORY_ITEM")

    def test_bad_page_metadata_fails_closed(self):
        bad = page(2, [row("id-1")], total=1)
        report = summarize_pages([bad], observed_at=NOW)
        self.assertEqual(report["reason_code"], "BILLING_HISTORY_PAGE_METADATA_MISMATCH")

    def test_invalid_amount_fails_closed(self):
        invalid = page(1, [row("id-1", amount=float("nan"))], total=1)
        with self.assertRaisesRegex(BillingHistoryError, "BILLING_AMOUNT_INVALID"):
            summarize_pages([invalid], observed_at=NOW)

    def test_identity_and_raw_fields_never_leak(self):
        report = summarize_pages(
            [page(1, [row("sensitive-id")], total=1)],
            observed_at=NOW,
        )
        self.assertNotIn("sensitive-id", str(report))
        self.assertFalse(report["raw_response_persisted"])
        self.assertFalse(report["invoice_ids_or_urls_persisted"])


if __name__ == "__main__":
    unittest.main()
