from __future__ import annotations

import hashlib
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture_execution import (
    ContextForwardExecutionError,
    canonical_json_bytes,
    require_execution_window,
    sha256_bytes,
    validate_execution_config,
    validate_existing_one_shot_state,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/context_forward_capture_execution_v0_1.json"
PREPARED = ROOT / "config/context_forward_capture_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/context-forward-capture-execution-v0-1.yml"
RECEIPT = ROOT / "research/receipts/2026-09-04-context-forward-capture-execution-v0-1-authority.json"
CONVERGENCE = ROOT / "config/project_convergence_v0_1.json"


class ContextForwardCaptureExecutionV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_bytes = CONFIG.read_bytes()
        self.config = json.loads(self.config_bytes)
        self.prepared_bytes = PREPARED.read_bytes()

    def test_execution_authority_validates(self) -> None:
        validate_execution_config(self.config, prepared_capture_bytes=self.prepared_bytes)

    def test_execution_window_is_strictly_post_v012(self) -> None:
        with self.assertRaisesRegex(ContextForwardExecutionError, "before not_before"):
            require_execution_window(
                self.config,
                observed_at=datetime(2026, 9, 12, 3, 59, 59, tzinfo=UTC),
            )
        require_execution_window(
            self.config,
            observed_at=datetime(2026, 9, 12, 4, 0, 0, tzinfo=UTC),
        )
        with self.assertRaisesRegex(ContextForwardExecutionError, "expired"):
            require_execution_window(
                self.config,
                observed_at=datetime(2026, 9, 19, 4, 0, 0, tzinfo=UTC),
            )

    def test_one_shot_state_is_idempotent_and_partial_state_fails_closed(self) -> None:
        self.assertEqual(
            validate_existing_one_shot_state(snapshot_payload=None, receipt_payload=None),
            "EMPTY",
        )
        snapshot = b'{"schema":"context-forward-snapshot-v0.1"}\n'
        receipt = canonical_json_bytes(
            {
                "schema": "context-forward-capture-execution-receipt-v0.1",
                "status": "PASS",
                "snapshot_sha256": sha256_bytes(snapshot),
            }
        )
        self.assertEqual(
            validate_existing_one_shot_state(
                snapshot_payload=snapshot,
                receipt_payload=receipt,
            ),
            "COMPLETE",
        )
        with self.assertRaisesRegex(ContextForwardExecutionError, "partial snapshot"):
            validate_existing_one_shot_state(snapshot_payload=snapshot, receipt_payload=None)
        with self.assertRaisesRegex(ContextForwardExecutionError, "receipt exists without snapshot"):
            validate_existing_one_shot_state(snapshot_payload=None, receipt_payload=receipt)

    def test_workflow_is_manual_only_and_has_no_cron(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertIn("context_forward_capture_execution_v0_1.json", workflow)

    def test_no_4h_schedule_or_downstream_trading_authority(self) -> None:
        self.assertFalse(self.config["execution"]["workflow_schedule_authorized"])
        self.assertFalse(self.config["next_stage_boundary"]["four_hour_schedule_authorized"])
        authority = self.config["authority"]
        for key in (
            "historical_backfill_authorized",
            "workflow_schedule_authorized",
            "holdout_access_authorized",
            "replacement_holdout_tuning_authorized",
            "strategy_parameter_change_authorized",
            "strategy_score_change_authorized",
            "risk_change_authorized",
            "leverage_change_authorized",
            "short_execution_authorized",
            "model_promotion_authorized",
            "trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(authority[key], key)

    def test_raw_payload_persistence_remains_disabled(self) -> None:
        storage = self.config["storage"]
        self.assertFalse(storage["raw_payload_persistence_authorized"])
        self.assertTrue(storage["normalized_snapshot_persistence_authorized"])
        self.assertTrue(storage["receipt_written_last"])
        self.assertEqual(storage["free_only_hard_stop_bytes"], 8_000_000_000)

    def test_authority_receipt_binds_exact_config_sha256(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["config_sha256"], hashlib.sha256(self.config_bytes).hexdigest())
        self.assertFalse(receipt["workflow_schedule_authorized"])
        self.assertFalse(receipt["holdout_access_authorized"])
        self.assertFalse(receipt["live_trading_authorized"])

    def test_new_manual_workflow_is_classified_without_changing_cron_count(self) -> None:
        convergence = json.loads(CONVERGENCE.read_text(encoding="utf-8"))
        groups = convergence["workflow_groups"]
        classified = {
            name
            for values in groups.values()
            for name in values
        }
        self.assertIn("context-forward-capture-execution-v0-1.yml", classified)
        scheduled = convergence["scheduled_workflows"]
        cron_entries = [
            item
            for values in scheduled.values()
            for item in values
            if isinstance(item, dict) and item.get("cron_utc")
        ]
        self.assertEqual(len(cron_entries), 7)


if __name__ == "__main__":
    unittest.main()
