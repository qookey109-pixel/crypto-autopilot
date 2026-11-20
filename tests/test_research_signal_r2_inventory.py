"""Whole-bucket capacity checks for the daily research collector, with no network."""
import unittest
from unittest.mock import Mock, call

from crypto_autopilot.research.signal_ingest_v0_2 import current_bucket_bytes


def store_for(*pages):
    store = Mock(bucket="fixture")
    store.client.list_objects_v2.side_effect = pages
    return store


class ResearchInventoryTests(unittest.TestCase):
    def test_complete_listing_totals_bytes_and_follows_exact_token(self):
        store = store_for(
            {"Contents": [{"Key": "a", "Size": 8}], "KeyCount": 1,
             "IsTruncated": True, "NextContinuationToken": "next"},
            {"Contents": [{"Key": "b", "Size": 0}, {"Key": "c", "Size": 5}],
             "KeyCount": 2, "IsTruncated": False},
        )
        self.assertEqual(current_bucket_bytes(store), 13)
        self.assertEqual(store.client.list_objects_v2.call_args_list, [
            call(Bucket="fixture", MaxKeys=1000),
            call(Bucket="fixture", MaxKeys=1000, ContinuationToken="next"),
        ])
        self.assertEqual(current_bucket_bytes(store_for({"KeyCount": 0, "IsTruncated": False})), 0)

    def test_incomplete_or_inconsistent_page_cannot_establish_headroom(self):
        cases = (
            {}, {"IsTruncated": False},
            {"IsTruncated": False, "Prefix": "only/", "KeyCount": 0},
            {"IsTruncated": False, "Name": "other", "KeyCount": 0},
            {"IsTruncated": False, "KeyCount": False},
            {"IsTruncated": False, "Contents": [], "KeyCount": 1},
            {"IsTruncated": True, "Contents": []},
            {"IsTruncated": False, "Contents": [], "NextContinuationToken": "unexpected"},
            {"IsTruncated": False, "KeyCount": 0, "CommonPrefixes": [{"Prefix": "hidden/"}]},
            {"IsTruncated": False, "Contents": [{"Key": "a"}]},
            {"IsTruncated": False, "Contents": [{"Key": "a", "Size": -1}]},
            {"IsTruncated": False, "Contents": [{"Key": "a", "Size": True}]},
        )
        for page in cases:
            with self.subTest(page=page), self.assertRaises(ValueError):
                current_bucket_bytes(store_for(page))

    def test_repeated_key_or_token_stops_on_second_page(self):
        first = {"Contents": [{"Key": "a", "Size": 8}], "IsTruncated": True,
                 "NextContinuationToken": "next"}
        for second in ({"Contents": first["Contents"], "IsTruncated": False},
                       {"Contents": [], "IsTruncated": True, "NextContinuationToken": "next"}):
            store = store_for(first, second)
            with self.subTest(page=second), self.assertRaises(ValueError):
                current_bucket_bytes(store)
            self.assertEqual(store.client.list_objects_v2.call_count, 2)

    def test_page_limit_never_accepts_a_partial_total_or_fetches_an_extra_page(self):
        pages = [{"IsTruncated": True, "Contents": [{"Key": str(i), "Size": 1}],
                  "NextContinuationToken": str(i)} for i in range(32)]
        store = store_for(*pages)
        with self.assertRaises(ValueError):
            current_bucket_bytes(store)
        self.assertEqual(store.client.list_objects_v2.call_count, 32)
        pages[-1] = {"IsTruncated": False, "KeyCount": 0}
        self.assertEqual(current_bucket_bytes(store_for(*pages)), 31)
