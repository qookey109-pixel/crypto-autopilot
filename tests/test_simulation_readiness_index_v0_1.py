from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "research/status/simulation-readiness-v0-1.json"


class SimulationReadinessIndexV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = json.loads(INDEX.read_text(encoding="utf-8"))

    def test_index_is_non_authority_and_not_ready(self) -> None:
        self.assertEqual(self.index["schema"], "qookey-simulation-readiness-v0.1")
        self.assertFalse(self.index["authority"])
        self.assertEqual(self.index["status_type"], "READ_ONLY_OPERATIONAL_INDEX")
        self.assertEqual(self.index["overall"], "NOT_READY")
        self.assertFalse(self.index["full_simulation_ready"])
        self.assertFalse(self.index["full_universe_ready"])

    def test_fixed_btc_ready_does_not_promote_full_universe(self) -> None:
        btc = self.index["btc_fixed_sample"]
        self.assertEqual(btc["state"], "READY")
        self.assertTrue(btc["does_not_imply_full_universe_ready"])
        self.assertFalse(self.index["full_universe_ready"])

    def test_v012_missing_slots_remain_fail_closed(self) -> None:
        metadata = self.index["metadata_stability"]
        self.assertEqual(metadata["state"], "BLOCKED_V0_12_COMPLETE_PASS_INELIGIBLE")
        self.assertEqual(metadata["display_state"], "BLOCKED")
        self.assertEqual(
            metadata["display_eligibility"],
            "COMPLETE_194_SLOT_PASS_INELIGIBLE",
        )
        self.assertEqual(metadata["required_hourly_slot_count"], 194)
        self.assertTrue(metadata["all_hourly_slots_required"])
        self.assertEqual(
            metadata["irreversibly_missing_hourly_slots_utc"],
            ["2026-09-04T02:00:00Z", "2026-09-04T03:00:00Z"],
        )
        self.assertFalse(metadata["complete_window_pass_eligible"])
        self.assertFalse(metadata["partial_window_may_pass"])
        self.assertFalse(metadata["retroactive_backfill_authorized"])
        self.assertFalse(metadata["later_observation_can_restore_missing_slots"])
        self.assertTrue(metadata["v0_12_capture_observation_may_continue"])
        self.assertFalse(metadata["production_stability_evaluation_authorized"])
        self.assertEqual(metadata["latest_observed_scheduled_run_id"], 34614741624)
        self.assertEqual(metadata["latest_observed_scheduled_run_number"], 55)
        self.assertEqual(
            metadata["latest_observed_run_outcome"],
            "FAIL_PROVIDER_CAPTURE_RENDER_HTTP_502",
        )
        self.assertTrue(metadata["render_recovery_occurred_after_latest_observed_failure"])
        self.assertEqual(
            metadata["post_recovery_formal_schedule_evidence_state"],
            "AWAITING_NEW_FORMAL_RUN_EVIDENCE",
        )
        self.assertEqual(metadata["replacement_holdout_state"], "FROZEN_UNOPENED")

    def test_context_forward_does_not_activate_v02_schedule(self) -> None:
        context = self.index["context_forward_v0_1"]
        self.assertEqual(context["state"], "AUTHORIZED_PENDING_ONE_SHOT")
        self.assertEqual(context["max_successful_captures"], 1)
        self.assertEqual(context["automatic_retries"], 0)
        self.assertFalse(context["four_hour_schedule_authorized"])

    def test_safety_boundary_remains_closed(self) -> None:
        boundary = self.index["safety_boundary"]
        self.assertTrue(boundary)
        self.assertTrue(all(value is False for value in boundary.values()))


if __name__ == "__main__":
    unittest.main()
