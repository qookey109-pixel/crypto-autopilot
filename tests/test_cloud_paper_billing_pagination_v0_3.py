from datetime import UTC, datetime
import unittest
from scripts.cloud_paper_billing_pagination_v0_3 import collect_pages, summarize_pages

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def page(n, ids, **extra):
    return {"success": True, "errors": [], "result":
            [{"id": i, "amount": 0, "currency": "USD"} for i in ids],
            "result_info": {"page": n, "per_page": 2, **extra}}


class PaginationTests(unittest.TestCase):
    def report(self, pages, **kwargs):
        return summarize_pages(pages, observed_at=NOW, page_size=2, **kwargs)

    def test_optional_totals_and_terminal(self):
        r = self.report([page(1, ["private-a"]), page(2, [])])
        self.assertEqual(r["status"], "READY_FOR_BILLING_REVIEW")
        self.assertFalse(r["complete_history_coverage"])
        self.assertTrue(r["bounded_traversal_complete"])
        self.assertFalse(r["atomic_snapshot_proven"])
        self.assertEqual(r["zero_cost_conclusion"], "UNKNOWN")
        self.assertNotIn("private-a", str(r))

    def test_short_page_alone_is_not_terminal(self):
        self.assertFalse(self.report([page(1, ["a"])])["complete_history_coverage"])

    def test_empty_history(self):
        self.assertEqual(self.report([page(1, [])])["returned_row_count"], 0)
        self.assertTrue(self.report([page(1, [])])["traversal_terminal_seen"])

    def test_supplied_counts_validated(self):
        self.assertEqual(self.report([page(1, ["a"], count=2)])["reason_code"],
                         "BILLING_HISTORY_PAGE_COUNT_MISMATCH")

    def test_total_mismatch(self):
        r = self.report([page(1, ["a"], total_count=2), page(2, [], total_count=2)])
        self.assertEqual(r["reason_code"], "BILLING_HISTORY_TOTAL_MISMATCH")

    def test_changed_total(self):
        r = self.report([page(1, ["a"], total_count=2), page(2, [], total_count=1)])
        self.assertEqual(r["reason_code"], "BILLING_HISTORY_TOTAL_CHANGED_DURING_READ")

    def test_duplicate_and_missing_identity(self):
        r = self.report([page(1, ["a"]), page(2, ["a"])])
        self.assertEqual(r["reason_code"], "DUPLICATE_BILLING_HISTORY_ITEM")
        bad = page(1, ["a"])
        del bad["result"][0]["id"]
        self.assertEqual(self.report([bad])["reason_code"], "BILLING_HISTORY_ITEM_ID_INVALID")

    def test_boolean_metadata_and_redacted_diagnostic(self):
        r = self.report([page(1, ["a"], count=True)])
        self.assertEqual(r["reason_code"], "BILLING_HISTORY_PAGE_METADATA_INVALID")
        self.assertEqual(r["pagination_metadata_diagnostics"][0]["fields"]["count"]["type"],
                         "boolean")

    def test_bound_before_fetch_and_no_retry(self):
        calls = []
        def fetch(n, size):
            calls.append(n)
            return page(n, ["a"])
        _, r = collect_pages(fetch, observed_at=NOW, page_size=2)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(r["reason_code"], "DUPLICATE_BILLING_HISTORY_ITEM")
        calls.clear()
        with self.assertRaises(ValueError):
            collect_pages(fetch, observed_at=NOW, max_pages=11)
        self.assertEqual(calls, [])

    def test_cap_and_data_after_terminal(self):
        r = self.report([page(1, ["a"])], max_pages=1)
        self.assertEqual(r["reason_code"], "BILLING_HISTORY_PAGE_CAP_REACHED_WITHOUT_TERMINAL")
        self.assertFalse(r["complete_history_coverage"])
        self.assertEqual(self.report([page(1, []), page(2, [])])["reason_code"],
                         "BILLING_HISTORY_DATA_AFTER_TERMINAL")


    def test_supplied_total_reconciled_with_empty_terminal(self):
        r = self.report([page(1, ["a", "b"], total_count=2),
                         page(2, [], total_count=2)])
        self.assertTrue(r["complete_history_coverage"])
        self.assertFalse(r["atomic_snapshot_proven"])

    def test_bad_identity_and_changed_size_stop(self):
        for bad in (page(2, ["a"]), page(1, ["a"])):
            if bad["result_info"]["page"] == 1:
                bad["result_info"]["per_page"] = 1
            self.assertEqual(self.report([bad])["reason_code"],
                             "BILLING_HISTORY_PAGE_METADATA_MISMATCH")

    def test_oversized_rows_and_item_cap(self):
        self.assertEqual(self.report([page(1, ["a", "b", "c"])])["reason_code"],
                         "BILLING_HISTORY_PAGE_SIZE_EXCEEDED")
        self.assertEqual(self.report([page(1, ["a", "b"])], max_items=1)["reason_code"],
                         "BILLING_HISTORY_ITEM_CAP_EXCEEDED")

    def test_partial_valid_rows_retained_on_invalid_later_page(self):
        r = self.report([page(1, ["a"]), page(3, ["b"])])
        self.assertEqual(r["returned_row_count"], 1)
        self.assertFalse(r["complete_history_coverage"])

    def test_invalid_row_returns_safe_reason(self):
        bad = page(1, ["a"])
        bad["result"][0]["amount"] = float("nan")
        r = self.report([bad])
        self.assertEqual(r["reason_code"], "BILLING_AMOUNT_INVALID")
        self.assertEqual(r["items"], [])

    def test_errors_and_missing_page_information(self):
        for bad in ({"success": True, "errors": [{"private": "hidden"}]},
                    {"success": True, "result": [], "result_info": None}):
            r = self.report([bad])
            self.assertEqual(r["status"], "REVIEW_REQUIRED")
            self.assertNotIn("hidden", str(r))

    def test_fetch_failure_is_not_retried(self):
        calls = []
        def fetch(n, size):
            calls.append(n)
            raise TimeoutError()
        with self.assertRaises(TimeoutError):
            collect_pages(fetch, observed_at=NOW, page_size=2)
        self.assertEqual(calls, [1])


if __name__ == "__main__":
    unittest.main()
