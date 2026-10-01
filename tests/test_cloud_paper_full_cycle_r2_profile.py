from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "measure_cloud_paper_full_cycle_r2_v0_1.py"
SPEC = importlib.util.spec_from_file_location("full_cycle_r2_profile_test", PATH)
assert SPEC is not None and SPEC.loader is not None
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


class CloudPaperFullCycleR2ProfileTests(unittest.TestCase):
    def test_complete_cycle_preserves_existing_assertions_and_budget_accounting(self):
        report = profile.build_report()
        self.assertEqual(report["external_access"]["r2_requests"], 0)
        self.assertEqual(len(report["scenarios"]), 4)
        for scenario in report["scenarios"]:
            self.assertEqual(scenario["fixture_assertions"], "PASS")
            for row in scenario["stores"]:
                operations = row["s3_compatible_operation_calls"]
                self.assertEqual(
                    row["budget_reservations"]["R2_CLASS_A"],
                    operations.get("PUT", 0) + operations.get("LIST", 0),
                )
                self.assertEqual(
                    row["budget_reservations"]["R2_CLASS_B"], operations.get("GET", 0),
                )
                self.assertEqual(
                    row["reserved_put_application_payload_bytes"],
                    row["put_application_payload_bytes"],
                )
                self.assertEqual(
                    row["guard_attempted_usage"]["new_bytes"],
                    row["reserved_put_application_payload_bytes"],
                )
        cycle = report["scenarios"][1]["stores"][0]
        self.assertEqual(len(cycle["completed_slots"]), 3)
        self.assertEqual(cycle["stored_objects"], 26)

    def test_pagination_changes_operations_without_changing_saved_account(self):
        method = "test_qualified_fixture_completes_entry_exit_and_no_trade_through_composition"
        standard = profile.profile_fixture("standard", method)["stores"][0]
        paged = profile.profile_fixture("paged", method, page_size=2)["stores"][0]
        self.assertEqual(standard["stored_objects"], paged["stored_objects"])
        self.assertEqual(
            standard["stored_object_payload_bytes"], paged["stored_object_payload_bytes"],
        )
        self.assertGreater(
            paged["s3_compatible_operation_calls"]["LIST"],
            standard["s3_compatible_operation_calls"]["LIST"],
        )
        self.assertEqual(
            paged["budget_reservations"]["R2_CLASS_A"],
            paged["s3_compatible_operation_calls"]["LIST"]
            + paged["s3_compatible_operation_calls"]["PUT"],
        )


if __name__ == "__main__":
    unittest.main()
