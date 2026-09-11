from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture_execution import (
    ContextForwardExecutionError,
)
from crypto_autopilot.providers.context_forward_capture_report import (
    validate_context_forward_execution_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/context_forward_capture_execution_v0_1.json"


class ContextForwardCaptureReportV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        storage = self.config["storage"]
        self.pass_report = {
            "schema": "context-forward-capture-execution-report-v0.1",
            "status": "PASS",
            "stage": "CONTEXT_FORWARD_CAPTURE_ONE_SHOT_FROZEN_V0_1",
            "captured_at_utc": "2026-09-12T04:00:05Z",
            "provider_requests_performed": 2,
            "automatic_retries_performed": 0,
            "bucket_bytes_before_provider": 22_120_404,
            "bucket_bytes_before_write": 22_120_404,
            "planned_write_bytes": 2_048,
            "hard_stop_bytes": 8_000_000_000,
            "snapshot": {
                "action": "UPLOAD",
                "bucket": "test-bucket",
                "key": storage["snapshot_key"],
                "bytes": 1_024,
                "sha256": "a" * 64,
                "etag": "etag-a",
            },
            "receipt": {
                "action": "UPLOAD",
                "bucket": "test-bucket",
                "key": storage["receipt_key"],
                "bytes": 1_024,
                "sha256": "b" * 64,
                "etag": "etag-b",
            },
            "receipt_written_last": True,
            "raw_payloads_persisted": False,
            "historical_backfill_performed": False,
            "holdout_accessed": False,
            "strategy_changed": False,
            "short_execution_authorized": False,
            "model_promotion_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }

    def test_valid_pass_report(self) -> None:
        self.assertEqual(
            validate_context_forward_execution_report(
                self.pass_report,
                config=self.config,
            ),
            "PASS",
        )

    def test_valid_already_complete_report(self) -> None:
        storage = self.config["storage"]
        report = {
            "schema": "context-forward-capture-execution-report-v0.1",
            "status": "ALREADY_COMPLETE",
            "stage": "ONE_SHOT_SUCCESS_ALREADY_FROZEN",
            "provider_requests_performed": 0,
            "r2_writes_performed": False,
            "snapshot_key": storage["snapshot_key"],
            "receipt_key": storage["receipt_key"],
            "holdout_accessed": False,
            "historical_backfill_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
        self.assertEqual(
            validate_context_forward_execution_report(report, config=self.config),
            "ALREADY_COMPLETE",
        )

    def test_rejects_downstream_authority_change(self) -> None:
        report = deepcopy(self.pass_report)
        report["live_trading_authorized"] = True
        with self.assertRaisesRegex(ContextForwardExecutionError, "live_trading_authorized"):
            validate_context_forward_execution_report(report, config=self.config)

    def test_rejects_wrong_storage_key(self) -> None:
        report = deepcopy(self.pass_report)
        report["receipt"]["key"] = "context/wrong/receipt.json"
        with self.assertRaisesRegex(ContextForwardExecutionError, "receipt.key changed"):
            validate_context_forward_execution_report(report, config=self.config)

    def test_rejects_budget_overrun(self) -> None:
        report = deepcopy(self.pass_report)
        report["bucket_bytes_before_write"] = 7_999_999_000
        report["planned_write_bytes"] = 2_000
        with self.assertRaisesRegex(ContextForwardExecutionError, "exceeded R2 hard stop"):
            validate_context_forward_execution_report(report, config=self.config)

    def test_rejects_invalid_sha256(self) -> None:
        report = deepcopy(self.pass_report)
        report["snapshot"]["sha256"] = "not-a-sha"
        with self.assertRaisesRegex(ContextForwardExecutionError, "snapshot.sha256"):
            validate_context_forward_execution_report(report, config=self.config)


if __name__ == "__main__":
    unittest.main()
