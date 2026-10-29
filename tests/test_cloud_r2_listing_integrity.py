"""Synthetic integrity tests for complete R2 namespace listings."""
import unittest

from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Policy, BudgetedR2Store


class Pages:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.pages)


class CloudR2ListingIntegrityTests(unittest.TestCase):
    def store(self, pages):
        client = Pages(pages)
        return BudgetedR2Store(
            client=client, bucket="fixture", before_external=lambda operation, size: None,
            policy=BudgetedR2Policy(maximum_list_pages=3, maximum_list_keys_per_page=2),
        ), client

    def test_complete_two_pages_preserve_all_keys(self):
        store, client = self.store([
            {"Contents": [{"Key": "p/a"}], "IsTruncated": True,
             "NextContinuationToken": "next"},
            {"Contents": [{"Key": "p/b"}], "IsTruncated": False},
        ])
        self.assertEqual(store.list_keys("p/"), ("p/a", "p/b"))
        self.assertEqual(client.calls[1]["ContinuationToken"], "next")

    def test_unproven_or_invalid_inventory_is_rejected(self):
        cases = (
            {"Contents": []},
            {"IsTruncated": False},
            {"IsTruncated": False, "KeyCount": 1},
            {"Contents": [], "IsTruncated": False, "KeyCount": 1},
            {"Contents": [], "IsTruncated": False, "KeyCount": False},
            {"Contents": [], "IsTruncated": False, "NextContinuationToken": "extra"},
            {"Contents": [], "IsTruncated": None},
            {"Contents": [], "IsTruncated": 0},
            {"Contents": [{"Key": "other/a"}], "IsTruncated": False},
            {"Contents": [{"Key": "p/a"}, {"Key": "p/a"}], "IsTruncated": False},
            {"Contents": [{"Key": "p/a"}, {"Key": "p/b"}, {"Key": "p/c"}],
             "IsTruncated": False},
        )
        for page in cases:
            with self.subTest(page=page):
                store, _ = self.store([page])
                with self.assertRaises(ValueError):
                    store.list_keys("p/")

    def test_proven_empty_page_without_contents_is_accepted(self):
        store, _ = self.store([{"IsTruncated": False, "KeyCount": 0}])
        self.assertEqual(store.list_keys("p/"), ())

    def test_repeated_key_across_pages_is_rejected(self):
        store, _ = self.store([
            {"Contents": [{"Key": "p/a"}], "IsTruncated": True,
             "NextContinuationToken": "next"},
            {"Contents": [{"Key": "p/a"}], "IsTruncated": False},
        ])
        with self.assertRaises(ValueError):
            store.list_keys("p/")


if __name__ == "__main__":
    unittest.main()
