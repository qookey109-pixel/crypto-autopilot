from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture_execution import (
    ContextForwardExecutionError,
    canonical_json_bytes,
)
from crypto_autopilot.providers.context_forward_capture_receipt import (
    build_context_forward_evidence_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/context_forward_capture_execution_v0_1.json"


class ContextForwardCaptureReceiptV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        storage = self.config["storage"]
        self.report = {
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

    def _build(self, report: dict[str, object] | None = None) -> dict[str, object]:
        payload = self.report if report is None else report
        return build_context_forward_evidence_receipt(
            payload,
            config=self.config,
            report_bytes=canonical_json_bytes(payload),
            repository_main_sha="1" * 40,
            workflow_run_id=123,
            workflow_run_attempt=1,
            artifact_id=456,
            artifact_name="context-forward-capture-execution-123-1",
            artifact_zip_sha256="c" * 64,
        )

    def test_builds_non_authority_pass_receipt(self) -> None:
        receipt = self._build()
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["authority"])
        self.assertEqual(receipt["workflow"]["run_id"], 123)
        self.assertEqual(receipt["capture"]["snapshot_sha256"], "a" * 64)
        self.assertEqual(receipt["capture"]["receipt_sha256"], "b" * 64)
        self.assertFalse(receipt["safety_boundary"]["live_trading_authorized"])
        self.assertFalse(receipt["next_stage"]["v0_2_schedule_automatically_authorized"])
        self.assertTrue(receipt["next_stage"]["separate_reviewed_v0_2_authority_required"])

    def test_rejects_already_complete_as_first_success_evidence(self) -> None:
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
        with self.assertRaisesRegex(ContextForwardExecutionError, "first-success PASS"):
            self._build(report)

    def test_rejects_invalid_main_sha(self) -> None:
        with self.assertRaisesRegex(ContextForwardExecutionError, "repository_main_sha"):
            build_context_forward_evidence_receipt(
                self.report,
                config=self.config,
                report_bytes=canonical_json_bytes(self.report),
                repository_main_sha="bad",
                workflow_run_id=123,
                workflow_run_attempt=1,
                artifact_id=456,
                artifact_name="artifact",
                artifact_zip_sha256="c" * 64,
            )

    def test_rejects_invalid_artifact_sha(self) -> None:
        with self.assertRaisesRegex(ContextForwardExecutionError, "artifact_zip_sha256"):
            build_context_forward_evidence_receipt(
                self.report,
                config=self.config,
                report_bytes=canonical_json_bytes(self.report),
                repository_main_sha="1" * 40,
                workflow_run_id=123,
                workflow_run_attempt=1,
                artifact_id=456,
                artifact_name="artifact",
                artifact_zip_sha256="bad",
            )

    def test_rejects_report_safety_regression(self) -> None:
        report = deepcopy(self.report)
        report["holdout_accessed"] = True
        with self.assertRaisesRegex(ContextForwardExecutionError, "holdout_accessed"):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
