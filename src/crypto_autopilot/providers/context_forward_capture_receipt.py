from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from crypto_autopilot.providers.context_forward_capture_execution import (
    ContextForwardExecutionError,
)
from crypto_autopilot.providers.context_forward_capture_report import (
    validate_context_forward_execution_report,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _require_nonempty_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContextForwardExecutionError(f"{field} is missing")
    return value


def _require_positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContextForwardExecutionError(f"{field} must be a positive integer")
    return value


def build_context_forward_evidence_receipt(
    report: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    report_bytes: bytes,
    repository_main_sha: str,
    workflow_run_id: int,
    workflow_run_attempt: int,
    artifact_id: int,
    artifact_name: str,
    artifact_zip_sha256: str,
) -> dict[str, Any]:
    """Build a repository receipt candidate from a validated first-success report.

    This function is evidence-only. It does not authorize or perform provider,
    R2, schedule, holdout, strategy, order, or live-trading operations.
    """

    status = validate_context_forward_execution_report(report, config=config)
    if status != "PASS":
        raise ContextForwardExecutionError(
            "only a first-success PASS report can create the formal receipt candidate"
        )
    if _GIT_SHA_RE.fullmatch(repository_main_sha) is None:
        raise ContextForwardExecutionError("repository_main_sha must be a 40-char lowercase Git SHA")
    if _SHA256_RE.fullmatch(artifact_zip_sha256) is None:
        raise ContextForwardExecutionError("artifact_zip_sha256 is invalid")

    run_id = _require_positive_int(workflow_run_id, field="workflow_run_id")
    run_attempt = _require_positive_int(workflow_run_attempt, field="workflow_run_attempt")
    artifact = _require_positive_int(artifact_id, field="artifact_id")
    artifact_label = _require_nonempty_string(artifact_name, field="artifact_name")

    snapshot = report.get("snapshot") or {}
    receipt = report.get("receipt") or {}
    if not isinstance(snapshot, Mapping) or not isinstance(receipt, Mapping):
        raise ContextForwardExecutionError("validated report object records are missing")

    captured_at_utc = _require_nonempty_string(
        report.get("captured_at_utc"), field="captured_at_utc"
    )
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()

    return {
        "schema": "context-forward-capture-execution-evidence-v0.1",
        "status": "PASS",
        "stage": "CONTEXT_FORWARD_CAPTURE_V0_1_FIRST_SUCCESS_FROZEN_EVIDENCE",
        "authority": False,
        "evidence_type": "POST_EXECUTION_REPOSITORY_RECEIPT_CANDIDATE",
        "repository": "qookey109-pixel/crypto-autopilot",
        "repository_main_sha": repository_main_sha,
        "workflow": {
            "name": "Context Forward Capture Execution V0.1",
            "run_id": run_id,
            "run_attempt": run_attempt,
            "artifact_id": artifact,
            "artifact_name": artifact_label,
            "artifact_zip_sha256": artifact_zip_sha256,
            "report_json_sha256": report_sha256,
        },
        "capture": {
            "captured_at_utc": captured_at_utc,
            "provider": "coinpaprika",
            "provider_requests_performed": report["provider_requests_performed"],
            "automatic_retries_performed": report["automatic_retries_performed"],
            "bucket_bytes_before_provider": report["bucket_bytes_before_provider"],
            "bucket_bytes_before_write": report["bucket_bytes_before_write"],
            "planned_write_bytes": report["planned_write_bytes"],
            "hard_stop_bytes": report["hard_stop_bytes"],
            "snapshot_key": snapshot["key"],
            "snapshot_sha256": snapshot["sha256"],
            "snapshot_bytes": snapshot["bytes"],
            "receipt_key": receipt["key"],
            "receipt_sha256": receipt["sha256"],
            "receipt_bytes": receipt["bytes"],
            "receipt_written_last": True,
        },
        "safety_boundary": {
            "raw_payloads_persisted": False,
            "historical_backfill_performed": False,
            "holdout_accessed": False,
            "strategy_changed": False,
            "short_execution_authorized": False,
            "model_promotion_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
            "four_hour_schedule_authorized": False,
        },
        "next_stage": {
            "v0_2_schedule_automatically_authorized": False,
            "separate_reviewed_v0_2_authority_required": True,
        },
    }
