#!/usr/bin/env python3
"""Run the one-shot Pionex-native history and capacity pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.historical import backfill_klines
from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training.online_r2 import current_bucket_bytes

ROOT = Path(__file__).resolve().parents[1]
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


class PilotAuthorityError(RuntimeError):
    pass


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_utc(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise PilotAuthorityError("timestamp must be explicit UTC")
    return parsed


def utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise PilotAuthorityError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def create_store() -> R2Store:
    return R2Store(
        account_id=required("CLOUDFLARE_ACCOUNT_ID"), bucket=required("R2_BUCKET_NAME"),
        access_key_id=required("R2_ACCESS_KEY_ID"), secret_access_key=required("R2_SECRET_ACCESS_KEY"),
    )


def load_authority(config_path: Path, prepared_path: Path, receipt_path: Path) -> dict[str, Any]:
    config_bytes, prepared_bytes = config_path.read_bytes(), prepared_path.read_bytes()
    config, receipt = json.loads(config_bytes), json.loads(receipt_path.read_text())
    if receipt.get("config_sha256") != sha256_bytes(config_bytes):
        raise PilotAuthorityError("execution authority/config SHA-256 mismatch")
    if receipt.get("prepared_pool_config_sha256") != sha256_bytes(prepared_bytes):
        raise PilotAuthorityError("prepared pool SHA-256 mismatch")
    if config.get("status") != "EXECUTION_AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE":
        raise PilotAuthorityError("execution config is not authorized")
    if config.get("execution", {}).get("trigger") != "workflow_dispatch_only":
        raise PilotAuthorityError("pilot must remain workflow_dispatch only")
    authority = config.get("authority", {})
    for key in ("public_pionex_kline_reads_authorized", "production_r2_whole_bucket_headroom_reads_authorized", "production_r2_pilot_writes_authorized"):
        if authority.get(key) is not True:
            raise PilotAuthorityError(f"required authority missing: {key}")
    for key in ("automatic_schedule_authorized", "replacement_holdout_access_authorized", "historical_universe_membership_authorized", "backtest_admission_authorized", "training_authorized", "source_switch_authorized", "binance_relabel_as_pionex_authorized", "private_api_authorized", "automatic_model_promotion_authorized", "formal_trade_plan_authorized", "real_money_order_authorized", "live_trading_authorized"):
        if authority.get(key) is not False:
            raise PilotAuthorityError(f"prohibited authority changed: {key}")
    return config


def require_execution_window(config: dict[str, Any], observed_at: datetime) -> None:
    execution = config["execution"]
    if not parse_utc(execution["not_before_utc"]) <= observed_at < parse_utc(execution["stop_exclusive_utc"]):
        raise PilotAuthorityError("Pionex history pilot execution window is closed")


def put_immutable(store: R2Store, *, key: str, payload: bytes, content_type: str, role: str) -> dict[str, Any]:
    existing = store.get_bytes_if_exists(key)
    if existing is not None and existing != payload:
        raise PilotAuthorityError(f"immutable pilot object conflict: {key}")
    if existing is None:
        record = {"action": "UPLOAD", **asdict(store.put_bytes(key, payload, content_type=content_type, metadata={"provider": "pionex_public_futures", "role": role, "version": "v0.1"}))}
    else:
        record = {"action": "VERIFY_EXISTING", "bucket": store.bucket, "key": key, "bytes": len(existing), "sha256": sha256_bytes(existing), "etag": None}
    if store.get_bytes_verified(key, expected_sha256=str(record["sha256"])) != payload:
        raise PilotAuthorityError(f"R2 exact-byte readback mismatch: {key}")
    return record


def existing_complete(store: R2Store, config: dict[str, Any]) -> dict[str, Any] | None:
    payload = store.get_bytes_if_exists(config["storage"]["latest_pointer_key"])
    if payload is None:
        return None
    latest = json.loads(payload)
    prefix = str(config["storage"]["provider_namespace"]).rstrip("/") + "/run="
    if latest.get("schema") != "pionex-historical-research-pilot-latest-v0.1" or not str(latest.get("receipt_key")).startswith(prefix):
        raise PilotAuthorityError("pilot latest pointer identity mismatch")
    receipt = json.loads(store.get_bytes_verified(str(latest["receipt_key"]), expected_sha256=str(latest["receipt_sha256"])))
    if receipt.get("status") != "PASS" or receipt.get("symbol") != config["pilot"]["symbol"]:
        raise PilotAuthorityError("pilot latest pointer does not bind a PASS receipt")
    return latest


def run_pilot(config: dict[str, Any], store: R2Store, run_id: str, observed_at: datetime) -> dict[str, Any]:
    if not SAFE_RUN_ID.fullmatch(run_id):
        raise PilotAuthorityError("run-id must be a safe 1-96 character key component")
    storage, pilot = config["storage"], config["pilot"]
    before_provider = current_bucket_bytes(store)
    if before_provider + int(storage["maximum_planned_run_bytes"]) > int(storage["free_only_hard_stop_bytes"]):
        raise PilotAuthorityError("R2 FREE-ONLY headroom blocked before Pionex access")
    prior = existing_complete(store, config)
    if prior:
        return {"status": "ALREADY_COMPLETE", "stage": "PIONEX_HISTORICAL_RESEARCH_PILOT_ALREADY_COMPLETE", "provider_requests_performed": 0, "r2_writes_performed": False, "existing_run_id": prior["run_id"], "holdout_accessed": False, "live_trading_authorized": False}

    client = PionexPublicClient(requests_per_second=float(config["provider"]["requests_per_second_maximum"]))
    end_ms = int(observed_at.timestamp() * 1000)
    artifacts: list[tuple[str, bytes, dict[str, Any]]] = []
    for interval in pilot["intervals"]:
        result = backfill_klines(client, pilot["symbol"], interval, start_time_ms=0, end_time_ms=end_ms, page_limit=int(pilot["page_limit"]), max_pages=int(pilot["maximum_pages_per_interval"]))
        if not result.candles or not result.audit.ok:
            raise PilotAuthorityError(f"Pionex interval rejected before write: {interval}")
        parquet = candles_to_parquet(result.candles)
        if parquet_to_candles(parquet.payload) != list(result.candles):
            raise PilotAuthorityError(f"Parquet decode mismatch: {interval}")
        key = f"{storage['provider_namespace'].rstrip('/')}/run={run_id}/{pilot['symbol']}/{interval}.parquet"
        artifacts.append((key, parquet.payload, {"interval": interval, "rows": parquet.rows, "first_time_ms": parquet.first_time_ms, "last_time_ms": parquet.last_time_ms, "parquet_sha256": parquet.sha256, "parquet_bytes": len(parquet.payload), "pages_fetched": result.pages_fetched, "audit": asdict(result.audit)}))

    receipt = {"schema": "pionex-historical-research-pilot-receipt-v0.1", "status": "PASS", "provider": "pionex_public_futures", "symbol": pilot["symbol"], "run_id": run_id, "observed_at_utc": utc_text(observed_at), "intervals": [details for _, _, details in artifacts], "provider_splicing_performed": False, "silent_interpolation_performed": False, "holdout_accessed": False, "historical_universe_membership_authorized": False, "backtest_admission_authorized": False, "training_authorized": False, "source_switch_authorized": False, "binance_relabel_as_pionex_authorized": False, "trade_plan_authorized": False, "live_trading_authorized": False}
    receipt_payload = canonical_json_bytes(receipt)
    manifest = {"schema": "pionex-historical-research-pilot-manifest-v0.1", "status": "PASS", "provider": "pionex_public_futures", "run_id": run_id, "objects": [{"key": key, "bytes": len(payload), "sha256": sha256_bytes(payload)} for key, payload, _ in artifacts], "receipt_sha256": sha256_bytes(receipt_payload)}
    manifest_payload = canonical_json_bytes(manifest)
    planned = sum(len(payload) for _, payload, _ in artifacts) + len(receipt_payload) + len(manifest_payload)
    if planned > int(storage["maximum_planned_run_bytes"]):
        raise PilotAuthorityError("pilot output exceeded its authorized reservation")
    before_write = current_bucket_bytes(store)
    if before_write + planned > int(storage["free_only_hard_stop_bytes"]):
        raise PilotAuthorityError("R2 FREE-ONLY headroom blocked before write")

    records = [put_immutable(store, key=key, payload=payload, content_type="application/vnd.apache.parquet", role="history-pilot") for key, payload, _ in artifacts]
    prefix = f"{storage['provider_namespace'].rstrip('/')}/run={run_id}"
    receipt_key, manifest_key = f"{prefix}/receipt.json", f"{prefix}/manifest.json"
    records.append(put_immutable(store, key=receipt_key, payload=receipt_payload, content_type="application/json", role="pilot-receipt"))
    records.append(put_immutable(store, key=manifest_key, payload=manifest_payload, content_type="application/json", role="pilot-manifest"))
    latest = {"schema": "pionex-historical-research-pilot-latest-v0.1", "provider": "pionex_public_futures", "run_id": run_id, "receipt_key": receipt_key, "receipt_sha256": sha256_bytes(receipt_payload), "manifest_key": manifest_key, "manifest_sha256": sha256_bytes(manifest_payload)}
    latest_payload = canonical_json_bytes(latest)
    pointer = store.put_bytes(storage["latest_pointer_key"], latest_payload, content_type="application/json", metadata={"provider": "pionex_public_futures", "role": "pilot-latest", "version": "v0.1"})
    if store.get_bytes_verified(storage["latest_pointer_key"], expected_sha256=pointer.sha256) != latest_payload:
        raise PilotAuthorityError("pilot latest pointer readback mismatch")
    return {"status": "PASS", "stage": "PIONEX_HISTORICAL_RESEARCH_PILOT_PUBLISHED_V0_1", "provider_requests_performed": sum(details["pages_fetched"] for _, _, details in artifacts), "r2_writes_performed": True, "r2_latest_pointer_written_last": True, "r2_bucket_bytes_before_provider": before_provider, "r2_bucket_bytes_before_write": before_write, "planned_write_bytes": planned, "intervals": [details for _, _, details in artifacts], "objects": records, "holdout_accessed": False, "historical_universe_membership_authorized": False, "backtest_admission_authorized": False, "training_authorized": False, "source_switch_authorized": False, "binance_relabel_as_pionex_authorized": False, "trade_plan_authorized": False, "live_trading_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/pionex_historical_research_execution_v0_1.json")
    parser.add_argument("--prepared-config", type=Path, default=ROOT / "config/pionex_historical_research_pool_v0_1.json")
    parser.add_argument("--authority", type=Path, default=ROOT / "research/receipts/2026-09-10-pionex-historical-research-execution-v0-1-authority.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observed-at-utc")
    args = parser.parse_args()
    output, observed_at = require_ephemeral_output(args.output), parse_utc(args.observed_at_utc)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        config = load_authority(args.config, args.prepared_config, args.authority)
        require_execution_window(config, observed_at)
        report = run_pilot(config, create_store(), args.run_id, observed_at)
    except Exception as exc:
        report = {"schema": "pionex-historical-research-pilot-run-report-v0.1", "status": "FAIL", "stage": "PIONEX_HISTORICAL_RESEARCH_PILOT_FAILED_CLOSED", "reason": str(exc), "r2_writes_performed": False, "holdout_accessed": False, "live_trading_authorized": False}
        output.write_bytes(canonical_json_bytes(report))
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
    report["schema"], report["observed_at_utc"] = "pionex-historical-research-pilot-run-report-v0.1", utc_text(observed_at)
    output.write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
