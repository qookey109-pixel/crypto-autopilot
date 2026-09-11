from __future__ import annotations

import re
from typing import Any, Mapping

from crypto_autopilot.providers.context_forward_capture_execution import (
    ContextForwardExecutionError,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_dict(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContextForwardExecutionError(f"{field} must be an object")
    return value


def _require_false(report: Mapping[str, Any], *keys: str) -> None:
    for key in keys:
        if report.get(key, False) is not False:
            raise ContextForwardExecutionError(f"report safety boundary changed: {key}")


def _validate_object_record(
    record: Mapping[str, Any], *, expected_key: str, field: str
) -> None:
    if record.get("action") not in {"UPLOAD", "VERIFY_EXISTING"}:
        raise ContextForwardExecutionError(f"{field}.action is invalid")
    if record.get("key") != expected_key:
        raise ContextForwardExecutionError(f"{field}.key changed")
    if not isinstance(record.get("bucket"), str) or not record.get("bucket"):
        raise ContextForwardExecutionError(f"{field}.bucket is missing")
    byte_count = record.get("bytes")
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
        raise ContextForwardExecutionError(f"{field}.bytes is invalid")
    digest = record.get("sha256")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise ContextForwardExecutionError(f"{field}.sha256 is invalid")


def validate_context_forward_execution_report(
    report: Mapping[str, Any], *, config: Mapping[str, Any]
) -> str:
    """Validate a secret-free Context Forward V0.1 execution artifact.

    This is an evidence validator only. It does not authorize provider access,
    R2 access, retries, schedules, holdout access, or downstream trading work.
    """

    if report.get("schema") != "context-forward-capture-execution-report-v0.1":
        raise ContextForwardExecutionError("unexpected execution report schema")

    storage = _require_dict(config.get("storage") or {}, field="storage")
    snapshot_key = str(storage.get("snapshot_key") or "")
    receipt_key = str(storage.get("receipt_key") or "")
    hard_stop = int(storage.get("free_only_hard_stop_bytes") or 0)
    if not snapshot_key or not receipt_key:
        raise ContextForwardExecutionError("execution storage keys are missing")
    if hard_stop != 8_000_000_000:
        raise ContextForwardExecutionError("execution hard stop changed")

    _require_false(
        report,
        "raw_payloads_persisted",
        "historical_backfill_performed",
        "historical_backfill_authorized",
        "holdout_accessed",
        "strategy_changed",
        "short_execution_authorized",
        "model_promotion_authorized",
        "trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    )

    status = report.get("status")
    if status == "ALREADY_COMPLETE":
        if report.get("stage") != "ONE_SHOT_SUCCESS_ALREADY_FROZEN":
            raise ContextForwardExecutionError("ALREADY_COMPLETE stage changed")
        if report.get("provider_requests_performed") != 0:
            raise ContextForwardExecutionError(
                "ALREADY_COMPLETE must perform zero provider requests"
            )
        if report.get("r2_writes_performed") is not False:
            raise ContextForwardExecutionError("ALREADY_COMPLETE must perform zero R2 writes")
        if report.get("snapshot_key") != snapshot_key:
            raise ContextForwardExecutionError("ALREADY_COMPLETE snapshot key changed")
        if report.get("receipt_key") != receipt_key:
            raise ContextForwardExecutionError("ALREADY_COMPLETE receipt key changed")
        return status

    if status != "PASS":
        raise ContextForwardExecutionError("execution report is not PASS or ALREADY_COMPLETE")
    if report.get("stage") != "CONTEXT_FORWARD_CAPTURE_ONE_SHOT_FROZEN_V0_1":
        raise ContextForwardExecutionError("PASS stage changed")
    if report.get("provider_requests_performed") != 2:
        raise ContextForwardExecutionError("PASS must perform exactly two provider requests")
    if report.get("automatic_retries_performed") != 0:
        raise ContextForwardExecutionError("automatic retries must remain zero")
    if report.get("receipt_written_last") is not True:
        raise ContextForwardExecutionError("receipt must be written last")
    if report.get("hard_stop_bytes") != hard_stop:
        raise ContextForwardExecutionError("report hard stop does not match authority")

    bucket_before_provider = report.get("bucket_bytes_before_provider")
    bucket_before_write = report.get("bucket_bytes_before_write")
    planned_write_bytes = report.get("planned_write_bytes")
    for value, field in (
        (bucket_before_provider, "bucket_bytes_before_provider"),
        (bucket_before_write, "bucket_bytes_before_write"),
        (planned_write_bytes, "planned_write_bytes"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ContextForwardExecutionError(f"{field} is invalid")
    assert isinstance(bucket_before_provider, int)
    assert isinstance(bucket_before_write, int)
    assert isinstance(planned_write_bytes, int)
    if bucket_before_provider >= hard_stop:
        raise ContextForwardExecutionError("provider access occurred at or above R2 hard stop")
    if planned_write_bytes <= 0:
        raise ContextForwardExecutionError("planned_write_bytes must be positive")
    if bucket_before_write + planned_write_bytes > hard_stop:
        raise ContextForwardExecutionError("planned write exceeded R2 hard stop")

    snapshot = _require_dict(report.get("snapshot") or {}, field="snapshot")
    receipt = _require_dict(report.get("receipt") or {}, field="receipt")
    _validate_object_record(snapshot, expected_key=snapshot_key, field="snapshot")
    _validate_object_record(receipt, expected_key=receipt_key, field="receipt")
    return status
