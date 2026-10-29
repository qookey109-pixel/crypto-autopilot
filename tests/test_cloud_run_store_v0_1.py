"""Synthetic tests for strict Cloud Paper object inventory."""
import unittest

try:
    from crypto_autopilot.paper.cloud_run_store_v0_1 import CloudPaperRunStore
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.cloud_run_store_v0_1":
        raise
    CloudPaperRunStore = None


class Listing:
    def __init__(self, keys):
        self.keys = keys

    def list_keys(self, prefix):
        return self.keys


class CloudPaperInventoryTests(unittest.TestCase):
    def test_valid_ids_are_preserved(self):
        self.assertIsNotNone(CloudPaperRunStore)
        store = CloudPaperRunStore(Listing(("scope/live-state/a.json",)), prefix="scope")
        self.assertEqual(store.list_json_ids("live-state"), ("a",))

    def test_ambiguous_or_noncanonical_keys_are_not_silently_ignored(self):
        self.assertIsNotNone(CloudPaperRunStore)
        for key in ("scope/live-state/readme", "scope/live-state/nested/a.json",
                    "scope/live-state/ a.json", "scope/live-state/.json",
                    "other/live-state/a.json"):
            with self.subTest(key=key):
                store = CloudPaperRunStore(Listing((key,)), prefix="scope")
                with self.assertRaises(ValueError):
                    store.list_json_ids("live-state")


if __name__ == "__main__":
    unittest.main()
