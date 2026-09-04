from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.research.automation_health import WorkflowExpectation, evaluate_workflow


class CurrentAutomationWiringRegressionTests(unittest.TestCase):
    def test_pre_activation_failure_does_not_poison_conditional_health(self) -> None:
        expectation = WorkflowExpectation(
            workflow="conditional.yml",
            label="Conditional",
            mode="conditional",
            max_age_seconds=7200,
            active_from_utc="2026-09-04T02:00:00Z",
            allowed_events=("schedule",),
            allowed_conclusions=("success", "skipped"),
        )
        pre_activation_failure = {
            "id": 1,
            "event": "schedule",
            "status": "completed",
            "conclusion": "failure",
            "run_started_at": "2026-08-30T10:00:00Z",
            "html_url": "https://github.com/example/repo/actions/runs/1",
        }
        row = evaluate_workflow(
            expectation,
            [pre_activation_failure],
            now=datetime(2026, 9, 4, 5, 10, tzinfo=timezone.utc),
        )
        self.assertEqual(row["status"], "WAITING_DEPENDENCY")
        self.assertFalse(row["alert"])
        self.assertIsNone(row["last_run"])

    def test_training_workflow_uses_v0_1_2_authority(self) -> None:
        workflow = Path(".github/workflows/binance-usdm-detailed-training-v0-1.yml").read_text(
            encoding="utf-8"
        )
        current_authority = (
            "research/receipts/"
            "2026-08-29-binance-usdm-crypto-core-100-v0-1-2-authority.json"
        )
        superseded_authority = (
            "research/receipts/"
            "2026-08-24-binance-usdm-detailed-history-v0-1-1-bounded-authority.json"
        )
        self.assertIn("--config config/binance_usdm_detailed_history_v0_1_2.json", workflow)
        self.assertIn(f"--authority {current_authority}", workflow)
        self.assertNotIn(f"--authority {superseded_authority}", workflow)


if __name__ == "__main__":
    unittest.main()
