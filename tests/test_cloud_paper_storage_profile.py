from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "measure_cloud_paper_storage_v0_1.py"
SPEC = importlib.util.spec_from_file_location("storage_profile_command", PATH)
assert SPEC is not None and SPEC.loader is not None
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


class StorageProfileTests(unittest.TestCase):
    def test_exact_canonical_bytes_and_no_payload_leak(self):
        from crypto_autopilot.paper.run_store_v0_1 import _canonical_bytes
        payload = {"message": "台北", "value": 1.0}
        report = profile.summarize_objects({("state", "one"): payload})
        self.assertEqual(report["canonical_json_bytes"], len(_canonical_bytes(payload)))
        self.assertEqual(report["object_count"], 1)
        self.assertNotIn("message", report["by_kind"]["state"])

    def test_compact_report_fixture_reduces_canonical_storage_against_frozen_profile(self):
        scenario = profile.SCENARIOS[1]
        result = profile.profile_scenario(*scenario)
        storage = result["stores"][0]["final_storage"]
        # PR #658 artifact 11094147043 measured the same 3-slot fixture at
        # 206,181 total bytes and 70,352 cloud-report bytes before compaction.
        self.assertLess(storage["canonical_json_bytes"], 206181)
        self.assertLess(
            storage["by_kind"]["cloud-report"]["canonical_json_bytes"],
            70352,
        )

    def test_existing_fixture_still_passes_and_measurement_is_deterministic(self):
        scenario = profile.SCENARIOS[0]
        first = profile.profile_scenario(*scenario)
        second = profile.profile_scenario(*scenario)
        self.assertEqual(first, second)
        self.assertEqual(first["fixture_assertions"], "PASS")
        store = first["stores"][0]
        self.assertGreater(store["final_storage"]["canonical_json_bytes"], 0)
        self.assertIn("cloud-report", store["final_storage"]["by_kind"])
        self.assertEqual(len(store["completed_slots"]), 1)


if __name__ == "__main__":
    unittest.main()
