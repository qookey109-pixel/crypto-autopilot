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
        self.assertTrue(r["complete_history_coverage"])
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


if __name__ == "__main__":
    unittest.main()
