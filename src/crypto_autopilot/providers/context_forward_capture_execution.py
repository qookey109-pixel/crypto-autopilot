from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Mapping


class ContextForwardExecutionError(ValueError):
    """Raised when Context Forward Capture Execution V0.1 violates authority."""


def git_blob_sha(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("utf-8")
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324 - Git object identity


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContextForwardExecutionError(f"{field} must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ContextForwardExecutionError(f"{field} must be explicit UTC")
    return parsed


def validate_execution_config(
    config: Mapping[str, Any], *, prepared_capture_bytes: bytes
) -> None:
    if config.get("version") != "0.1.0":
        raise ContextForwardExecutionError("unexpected execution authority version")
    if config.get("status") != "AUTHORIZED_ON_PROTECTED_MAIN_MERGE_MANUAL_ONE_SHOT_AFTER_NOT_BEFORE":
        raise ContextForwardExecutionError("unexpected execution authority status")

    source = config.get("source_prepared_capture") or {}
    if source.get("path") != "config/context_forward_capture_v0_1.json":
        raise ContextForwardExecutionError("prepared capture path changed")
    if source.get("git_blob_sha") != git_blob_sha(prepared_capture_bytes):
        raise ContextForwardExecutionError("prepared capture Git blob SHA mismatch")
    try:
        prepared = json.loads(prepared_capture_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContextForwardExecutionError("prepared capture config is invalid") from exc
    if prepared.get("version") != source.get("required_version"):
        raise ContextForwardExecutionError("prepared capture version mismatch")
    if prepared.get("status") != source.get("required_status"):
        raise ContextForwardExecutionError("prepared capture status mismatch")
    if (prepared.get("provider") or {}).get("name") != source.get("required_provider"):
        raise ContextForwardExecutionError("prepared capture provider mismatch")
    prepared_authority = prepared.get("authority") or {}
    if prepared_authority.get("provider_fetch_authorized") is not False:
        raise ContextForwardExecutionError("prepared V0.1 must remain non-executing")
    if prepared_authority.get("production_r2_write_authorized") is not False:
        raise ContextForwardExecutionError("prepared V0.1 must remain non-writing")

    execution = config.get("execution") or {}
    if execution.get("mode") != "MANUAL_ONE_SHOT":
        raise ContextForwardExecutionError("execution mode changed")
    if execution.get("workflow_dispatch_authorized") is not True:
        raise ContextForwardExecutionError("manual dispatch must be authorized")
    if execution.get("workflow_schedule_authorized") is not False:
        raise ContextForwardExecutionError("V0.1 schedule must remain disabled")
    if int(execution.get("max_successful_captures") or 0) != 1:
        raise ContextForwardExecutionError("V0.1 must authorize exactly one successful capture")
    if execution.get("automatic_retries") != 0:
        raise ContextForwardExecutionError("automatic retries must remain zero")
    not_before = _parse_utc(str(execution.get("not_before_utc")), field="not_before_utc")
    expires = _parse_utc(str(execution.get("expires_utc")), field="expires_utc")
    if not_before != datetime(2026, 9, 12, 4, 0, tzinfo=UTC):
        raise ContextForwardExecutionError("not-before boundary changed")
    if expires <= not_before:
        raise ContextForwardExecutionError("execution window is empty")
    if execution.get("request_order") != [
        "https://api.coinpaprika.com/v1/global",
        "https://api.coinpaprika.com/v1/tickers/eth-ethereum",
    ]:
        raise ContextForwardExecutionError("provider request order changed")
    if int(execution.get("request_timeout_seconds") or 0) != 20:
        raise ContextForwardExecutionError("request timeout changed")
    if int(execution.get("max_response_bytes") or 0) != 1_048_576:
        raise ContextForwardExecutionError("response size bound changed")

    storage = config.get("storage") or {}
    namespace = "context/market-regime/v0_1/forward-execution-v0_1/"
    if storage.get("provider") != "cloudflare_r2" or storage.get("namespace") != namespace:
        raise ContextForwardExecutionError("storage identity changed")
    if storage.get("snapshot_key") != namespace + "first-success/snapshot.json":
        raise ContextForwardExecutionError("snapshot key changed")
    if storage.get("receipt_key") != namespace + "first-success/receipt.json":
        raise ContextForwardExecutionError("receipt key changed")
    required_true = (
        "normalized_snapshot_persistence_authorized",
        "receipt_persistence_authorized",
        "receipt_written_last",
        "immutable_exact_byte_required",
        "postwrite_sha256_readback_required",
        "whole_bucket_inventory_before_provider_required",
        "whole_bucket_inventory_before_write_required",
    )
    for key in required_true:
        if storage.get(key) is not True:
            raise ContextForwardExecutionError(f"storage.{key} must be true")
    if storage.get("raw_payload_persistence_authorized") is not False:
        raise ContextForwardExecutionError("raw provider payload persistence must remain false")
    if int(storage.get("free_only_hard_stop_bytes") or 0) != 8_000_000_000:
        raise ContextForwardExecutionError("R2 hard stop changed")

    next_stage = config.get("next_stage_boundary") or {}
    if next_stage.get("four_hour_schedule_authorized") is not False:
        raise ContextForwardExecutionError("4H schedule cannot be authorized by V0.1")
    if next_stage.get("four_hour_schedule_requires_separate_v0_2_authority") is not True:
        raise ContextForwardExecutionError("separate V0.2 schedule authority must remain required")

    authority = config.get("authority") or {}
    required_authority_true = (
        "research_only",
        "provider_fetch_authorized_after_not_before",
        "production_r2_read_authorized_after_not_before",
        "production_r2_write_authorized_after_not_before",
    )
    for key in required_authority_true:
        if authority.get(key) is not True:
            raise ContextForwardExecutionError(f"authority.{key} must be true")
    for key, value in authority.items():
        if key not in required_authority_true and value is not False:
            raise ContextForwardExecutionError(f"authority.{key} must remain false")


def require_execution_window(config: Mapping[str, Any], *, observed_at: datetime) -> None:
    if observed_at.tzinfo is None or observed_at.utcoffset() != UTC.utcoffset(observed_at):
        raise ContextForwardExecutionError("observed_at must be explicit UTC")
    execution = config["execution"]
    not_before = _parse_utc(str(execution["not_before_utc"]), field="not_before_utc")
    expires = _parse_utc(str(execution["expires_utc"]), field="expires_utc")
    if observed_at < not_before:
        raise ContextForwardExecutionError("execution is blocked before not_before_utc")
    if observed_at >= expires:
        raise ContextForwardExecutionError("execution authority expired")


def validate_existing_one_shot_state(
    *,
    snapshot_payload: bytes | None,
    receipt_payload: bytes | None,
) -> str:
    if receipt_payload is None and snapshot_payload is None:
        return "EMPTY"
    if receipt_payload is None and snapshot_payload is not None:
        raise ContextForwardExecutionError("partial snapshot exists without receipt; manual review required")
    if receipt_payload is not None and snapshot_payload is None:
        raise ContextForwardExecutionError("receipt exists without snapshot; manual review required")
    assert receipt_payload is not None and snapshot_payload is not None
    try:
        receipt = json.loads(receipt_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContextForwardExecutionError("existing receipt is invalid") from exc
    if receipt.get("schema") != "context-forward-capture-execution-receipt-v0.1":
        raise ContextForwardExecutionError("existing receipt schema mismatch")
    if receipt.get("status") != "PASS":
        raise ContextForwardExecutionError("existing receipt is not PASS")
    if receipt.get("snapshot_sha256") != sha256_bytes(snapshot_payload):
        raise ContextForwardExecutionError("existing receipt snapshot SHA mismatch")
    return "COMPLETE"
