from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CurrentOperationsStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
        self.payload = json.loads(
            (ROOT / "research/status/current-operations-v0-2.json").read_text(
                encoding="utf-8"
            )
        )

    def test_machine_readable_status_matches_current_entrypoint(self) -> None:
        payload = self.payload
        current = self.current

        self.assertEqual(payload["schema"], "qookey-current-operations-v0.2")
        self.assertEqual(payload["updated_date"], "2026-09-16")
        self.assertEqual(payload["mode"], "PAPER_ONLY")
        self.assertEqual(payload["core100"]["history_status"], "COMPLETE")
        self.assertEqual(payload["core100"]["history_complete_shards"], 10)
        self.assertEqual(payload["core100"]["history_total_shards"], 10)
        self.assertFalse(payload["core100"]["history_reacquisition_required"])
        self.assertEqual(payload["core100"]["training_run_id"], 34918219864)
        self.assertEqual(
            payload["core100"]["model_quality_gate"]["status"], "REJECT"
        )
        self.assertFalse(
            payload["core100"]["model_quality_gate"]["automatic_promotion"]
        )

        replay = payload["core100"]["threshold_replay"]
        self.assertEqual(replay["run_id"], 34936331199)
        self.assertEqual(replay["workflow_conclusion"], "success")
        self.assertEqual(replay["supported_thresholds"], [])
        self.assertFalse(replay["threshold_change_supported"])
        self.assertFalse(replay["configured_threshold_changed"])

        reviewed_main = payload["reviewed_main_sha"]
        fingerprint = payload["core100"]["dataset_fingerprint"]
        self.assertIn(reviewed_main, current)
        self.assertIn(fingerprint, current)
        self.assertIn(str(payload["core100"]["training_run_id"]), current)
        self.assertIn(str(replay["run_id"]), current)
        self.assertIn("History COMPLETE", current)
        self.assertIn("Model Quality REJECT", current)
        self.assertNotIn("Training SKIPPED", current)
        self.assertNotIn("History 8/10", current)

    def test_pionex_current_main_rerun_is_explicitly_pending(self) -> None:
        pionex = self.payload["pionex_validation"]
        authority = pionex["authority"]

        self.assertEqual(pionex["boundary_fix_merged_pr"], 321)
        self.assertEqual(
            pionex["boundary_fix_main_sha"], self.payload["reviewed_main_sha"]
        )
        self.assertEqual(
            pionex["current_main_materialization_status"],
            "PENDING_MANUAL_DISPATCH",
        )
        self.assertTrue(authority["public_pionex_kline_reads"])
        self.assertTrue(authority["r2_validation_dataset_writes"])
        self.assertFalse(authority["private_api"])
        self.assertFalse(authority["account_data"])
        self.assertFalse(authority["replacement_holdout_access"])
        self.assertFalse(authority["training"])
        self.assertFalse(authority["source_switch"])
        self.assertFalse(authority["automatic_model_promotion"])
        self.assertFalse(authority["formal_trade_plan"])
        self.assertFalse(authority["real_money_orders"])
        self.assertFalse(authority["live_trading"])

    def test_agents_read_current_status_before_dated_status(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        current_pos = agents.find("`CURRENT_STATUS.md`")
        project_pos = agents.find("`PROJECT_STATUS.md`")
        self.assertGreaterEqual(current_pos, 0)
        self.assertGreater(project_pos, current_pos)
        self.assertIn("current-operations-v0-2.json", agents)

    def test_closed_authority_boundaries_remain_closed(self) -> None:
        gates = self.payload["gates"]
        self.assertEqual(gates["strategy_validation"], "CLOSED")
        self.assertEqual(gates["holdout"], "FROZEN_UNOPENED")
        self.assertEqual(gates["automatic_model_promotion"], "CLOSED")
        self.assertEqual(gates["formal_trade_plan"], "CLOSED")
        self.assertEqual(gates["real_money_orders"], "CLOSED")
        self.assertEqual(gates["live_trading"], "CLOSED")
        self.assertFalse(gates["source_switch_authorized"])

    def test_technical_debt_register_exists(self) -> None:
        register = (
            ROOT / "docs/TECH_DEBT_REGISTER_2026_09_16.md"
        ).read_text(encoding="utf-8")
        self.assertIn("TD-001", register)
        self.assertIn("TD-002", register)
        self.assertIn("TD-009", register)
        self.assertIn("control-plane", register)


if __name__ == "__main__":
    unittest.main()
