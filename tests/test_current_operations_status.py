from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CurrentOperationsStatusTests(unittest.TestCase):
    def test_machine_readable_status_matches_current_entrypoint(self) -> None:
        current = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
        payload = json.loads(
            (ROOT / "research/status/current-operations-v0-1.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(payload["schema"], "qookey-current-operations-v0.1")
        self.assertEqual(payload["updated_date"], "2026-09-15")
        self.assertEqual(payload["mode"], "PAPER_ONLY")
        self.assertEqual(payload["core100"]["history_status"], "COMPLETE")
        self.assertFalse(payload["core100"]["history_reacquisition_required"])
        self.assertEqual(payload["core100"]["training_run_id"], 34918219864)
        self.assertEqual(
            payload["core100"]["model_quality_gate"]["status"], "REJECT"
        )
        self.assertFalse(
            payload["core100"]["model_quality_gate"]["automatic_promotion"]
        )
        self.assertEqual(payload["gates"]["holdout"], "FROZEN_UNOPENED")
        self.assertEqual(payload["gates"]["live_trading"], "CLOSED")
        self.assertFalse(payload["gates"]["source_switch_authorized"])

        reviewed_main = payload["reviewed_main_sha"]
        fingerprint = payload["core100"]["dataset_fingerprint"]
        replay_run = str(payload["core100"]["active_threshold_replay"]["run_id"])
        self.assertIn(reviewed_main, current)
        self.assertIn(fingerprint, current)
        self.assertIn(replay_run, current)
        self.assertIn("History COMPLETE", current)
        self.assertIn("Model Quality REJECT", current)

    def test_agents_read_current_status_before_dated_status(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        current_pos = agents.find("`CURRENT_STATUS.md`")
        project_pos = agents.find("`PROJECT_STATUS.md`")
        self.assertGreaterEqual(current_pos, 0)
        self.assertGreater(project_pos, current_pos)

    def test_current_status_preserves_closed_authority_boundaries(self) -> None:
        payload = json.loads(
            (ROOT / "research/status/current-operations-v0-1.json").read_text(
                encoding="utf-8"
            )
        )
        gates = payload["gates"]
        self.assertEqual(gates["strategy_validation"], "CLOSED")
        self.assertEqual(gates["automatic_model_promotion"], "CLOSED")
        self.assertEqual(gates["formal_trade_plan"], "CLOSED")
        self.assertEqual(gates["real_money_orders"], "CLOSED")
        self.assertEqual(gates["live_trading"], "CLOSED")


if __name__ == "__main__":
    unittest.main()
