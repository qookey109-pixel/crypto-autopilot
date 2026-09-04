#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.providers.context_forward_capture import build_context_forward_snapshot
from crypto_autopilot.providers.context_forward_capture_execution import (
    ContextForwardExecutionError,
    canonical_json_bytes,
    require_execution_window,
    sha256_bytes,
    validate_execution_config,
    validate_existing_one_shot_state,
)
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training.online_r2 import current_bucket_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/context_forward_capture_execution_v0_1.json"
DEFAULT_PREPARED = ROOT / "config/context_forward_capture_v0_1.json"
DEFAULT_SOURCE_LINEAGE = ROOT / "config/context_source_lineage_v0_1.json"


def _required_secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ContextForwardExecutionError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def _create_store() -> R2Store:
    return R2Store(
        account_id=_required_secret("CLOUDFLARE_ACCOUNT_ID"),
        bucket=_required_secret("R2_BUCKET_NAME"),
        access_key_id=_required_secret("R2_ACCESS_KEY_ID"),
        secret_access_key=_required_secret("R2_SECRET_ACCESS_KEY"),
    )


def _fetch_once(url: str, *, timeout_seconds: int, max_bytes: int, user_agent: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise ContextForwardExecutionError(f"provider HTTP status rejected: {status}")
            payload = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise ContextForwardExecutionError(f"provider HTTP error: {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise ContextForwardExecutionError("provider request failed or timed out") from exc
    if not payload:
        raise ContextForwardExecutionError("provider returned an empty payload")
    if len(payload) > max_bytes:
        raise ContextForwardExecutionError("provider response exceeded max_response_bytes")
    return payload


def _put_immutable(store: R2Store, *, key: str, payload: bytes, role: str) -> dict[str, Any]:
    existing = store.get_bytes_if_exists(key)
    if existing is not None and existing != payload:
        raise ContextForwardExecutionError(f"immutable R2 object conflict: {key}")
    if existing is None:
        uploaded = store.put_bytes(
            key,
            payload,
            content_type="application/json",
            metadata={"provider": "coinpaprika", "role": role, "version": "v0.1"},
        )
        record = {"action": "UPLOAD", **asdict(uploaded)}
    else:
        record = {
            "action": "VERIFY_EXISTING",
            "bucket": store.bucket,
            "key": key,
            "bytes": len(existing),
            "sha256": sha256_bytes(existing),
            "etag": None,
        }
    restored = store.get_bytes_verified(key, expected_sha256=str(record["sha256"]))
    if restored != payload:
        raise ContextForwardExecutionError(f"R2 exact-byte round trip mismatch: {key}")
    return record


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(report))


def run(*, config_path: Path, prepared_path: Path, source_lineage_path: Path, output: Path) -> int:
    config_bytes = config_path.read_bytes()
    prepared_bytes = prepared_path.read_bytes()
    source_lineage_bytes = source_lineage_path.read_bytes()
    config = json.loads(config_bytes)
    prepared = json.loads(prepared_bytes)
    validate_execution_config(config, prepared_capture_bytes=prepared_bytes)

    observed_at = datetime.now(UTC)
    require_execution_window(config, observed_at=observed_at)

    store = _create_store()
    storage = config["storage"]
    snapshot_key = str(storage["snapshot_key"])
    receipt_key = str(storage["receipt_key"])
    hard_stop = int(storage["free_only_hard_stop_bytes"])

    existing_snapshot = store.get_bytes_if_exists(snapshot_key)
    existing_receipt = store.get_bytes_if_exists(receipt_key)
    state = validate_existing_one_shot_state(
        snapshot_payload=existing_snapshot,
        receipt_payload=existing_receipt,
    )
    if state == "COMPLETE":
        report = {
            "schema": "context-forward-capture-execution-report-v0.1",
            "status": "ALREADY_COMPLETE",
            "stage": "ONE_SHOT_SUCCESS_ALREADY_FROZEN",
            "provider_requests_performed": 0,
            "r2_writes_performed": False,
            "snapshot_key": snapshot_key,
            "receipt_key": receipt_key,
            "holdout_accessed": False,
            "historical_backfill_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
        _write_report(output, report)
        return 0

    bucket_before_provider = current_bucket_bytes(store)
    if bucket_before_provider >= hard_stop:
        raise ContextForwardExecutionError("R2 FREE-ONLY hard stop blocked before provider access")

    execution = config["execution"]
    timeout_seconds = int(execution["request_timeout_seconds"])
    max_bytes = int(execution["max_response_bytes"])
    user_agent = str(execution["user_agent"])
    request_order = list(execution["request_order"])

    global_payload = _fetch_once(
        request_order[0],
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
        user_agent=user_agent,
    )
    eth_payload = _fetch_once(
        request_order[1],
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
        user_agent=user_agent,
    )
    capture_at = datetime.now(UTC)
    capture_timestamp_ms = int(capture_at.timestamp() * 1000)
    snapshot = build_context_forward_snapshot(
        config=prepared,
        source_lineage_bytes=source_lineage_bytes,
        global_payload=global_payload,
        eth_payload=eth_payload,
        capture_timestamp_ms=capture_timestamp_ms,
    )
    snapshot_payload = canonical_json_bytes(snapshot.as_dict())
    receipt = {
        "schema": "context-forward-capture-execution-receipt-v0.1",
        "status": "PASS",
        "mode": "RESEARCH_FORWARD_CONTEXT_ONE_SHOT",
        "provider": "coinpaprika",
        "captured_at_utc": capture_at.isoformat().replace("+00:00", "Z"),
        "capture_timestamp_ms": capture_timestamp_ms,
        "execution_config_sha256": sha256_bytes(config_bytes),
        "prepared_capture_config_sha256": sha256_bytes(prepared_bytes),
        "snapshot_key": snapshot_key,
        "snapshot_sha256": sha256_bytes(snapshot_payload),
        "snapshot_bytes": len(snapshot_payload),
        "global_raw_payload_sha256": snapshot.global_raw_payload_sha256,
        "eth_raw_payload_sha256": snapshot.eth_raw_payload_sha256,
        "raw_payloads_persisted": False,
        "provider_requests_performed": 2,
        "automatic_retries_performed": 0,
        "historical_backfill_performed": False,
        "holdout_accessed": False,
        "strategy_changed": False,
        "short_execution_authorized": False,
        "model_promotion_authorized": False,
        "trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }
    receipt_payload = canonical_json_bytes(receipt)

    bucket_before_write = current_bucket_bytes(store)
    planned = len(snapshot_payload) + len(receipt_payload)
    if bucket_before_write + planned > hard_stop:
        raise ContextForwardExecutionError("R2 FREE-ONLY hard stop blocked before write")

    snapshot_record = _put_immutable(
        store, key=snapshot_key, payload=snapshot_payload, role="context-forward-snapshot"
    )
    receipt_record = _put_immutable(
        store, key=receipt_key, payload=receipt_payload, role="context-forward-receipt"
    )

    report = {
        "schema": "context-forward-capture-execution-report-v0.1",
        "status": "PASS",
        "stage": "CONTEXT_FORWARD_CAPTURE_ONE_SHOT_FROZEN_V0_1",
        "captured_at_utc": receipt["captured_at_utc"],
        "provider_requests_performed": 2,
        "automatic_retries_performed": 0,
        "bucket_bytes_before_provider": bucket_before_provider,
        "bucket_bytes_before_write": bucket_before_write,
        "planned_write_bytes": planned,
        "hard_stop_bytes": hard_stop,
        "snapshot": snapshot_record,
        "receipt": receipt_record,
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
    _write_report(output, report)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--prepared-config", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--source-lineage", type=Path, default=DEFAULT_SOURCE_LINEAGE)
    parser.add_argument("--output", type=Path, default=Path("context-forward-output/report.json"))
    args = parser.parse_args()
    return run(
        config_path=args.config,
        prepared_path=args.prepared_config,
        source_lineage_path=args.source_lineage,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
