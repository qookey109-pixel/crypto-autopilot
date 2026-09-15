#!/usr/bin/env python3
"""Materialize one bounded Pionex-native validation dataset after reviewed merge."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from crypto_autopilot.history.pionex_validation_materialization_v0_1 import (
    ValidationMaterializationRejected,
    asset_class_for_symbol,
    collect_partition,
    iter_partitions,
    json_bytes,
    partition_count,
    profile_for_symbol,
    require_execution_window,
    sha256_bytes,
    validate_config,
    validate_run_id,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_validation_dataset_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-15-pionex-validation-dataset-v0-1-authority.json"
CONFIG_SHA256 = "83972be4bd6bd04d264a1f136283c5b95cb5e200c86cf22be4f02664d0035cbc"


def load_authority() -> dict:
    config_bytes = CONFIG.read_bytes()
    if sha256_bytes(config_bytes) != CONFIG_SHA256:
        raise ValidationMaterializationRejected("validation config bytes changed")
    config = json.loads(config_bytes)
    receipt = json.loads(RECEIPT.read_bytes())
    if receipt.get("config_sha256") != CONFIG_SHA256 or receipt.get("config") != "config/pionex_validation_dataset_v0_1.json":
        raise ValidationMaterializationRejected("authority receipt does not bind validation config")
    if receipt.get("status") != config.get("status"):
        raise ValidationMaterializationRejected("authority receipt/config status mismatch")
    if receipt.get("execution_performed_by_this_receipt") is not False:
        raise ValidationMaterializationRejected("authority receipt cannot claim execution")
    validate_config(config)
    return config


def require_github_main_dispatch() -> str:
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise ValidationMaterializationRejected("fresh GitHub main workflow_dispatch attempt 1 required")
    run_id = "github-" + str(os.environ.get("GITHUB_RUN_ID") or "") + "-1"
    validate_run_id(run_id)
    return run_id


def _partition_prefix(config: dict, symbol: str, interval: str) -> str:
    cutoff_day = str(config["cutoff_exclusive_utc"]).split("T", 1)[0]
    namespace = str(config["storage"]["namespace"]).rstrip("/")
    return f"{namespace}/cutoff={cutoff_day}/symbol={symbol}/interval={interval}"


def _put_or_verify(store, key: str, payload: bytes, *, content_type: str, metadata: dict[str, str]) -> str:
    existing = store.get_bytes_if_exists(key)
    if existing is not None:
        if existing != payload:
            raise ValidationMaterializationRejected(f"immutable validation object conflict: {key}")
        return "VERIFY_EXISTING"
    store.put_bytes(key, payload, content_type=content_type, metadata=metadata)
    if store.get_bytes_verified(key, expected_sha256=sha256_bytes(payload)) != payload:
        raise ValidationMaterializationRejected(f"R2 exact-byte readback mismatch: {key}")
    return "UPLOAD"


def execute(config: dict, store, client, run_id: str, *, clock) -> dict:
    from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
    from crypto_autopilot.training.online_r2 import current_bucket_bytes

    validate_config(config)
    require_execution_window(config, now_ms=clock())
    validate_run_id(run_id)
    namespace = str(config["storage"]["namespace"]).rstrip("/")
    latest_key = f"{namespace}/latest.json"
    old_latest = store.get_bytes_if_exists(latest_key)
    if old_latest is not None:
        latest = json.loads(old_latest)
        if latest.get("config_sha256") != CONFIG_SHA256 or latest.get("status") != "PASS":
            raise ValidationMaterializationRejected("existing latest pointer does not match V0.1 authority")
        return {
            "status": "ALREADY_COMPLETE",
            "stage": "PIONEX_VALIDATION_DATASET_ALREADY_MATERIALIZED_V0_1",
            "manifest_key": latest.get("manifest_key"),
            "partition_count": latest.get("partition_count"),
            "provider_requests": 0,
            "r2_writes_performed": False,
        }

    current_bytes = current_bucket_bytes(store)
    hard_stop = int(config["storage"]["free_only_hard_stop_bytes"])
    reservation = int(config["storage"]["maximum_planned_run_bytes"])
    if current_bytes + reservation > hard_stop:
        raise ValidationMaterializationRejected("FREE-ONLY R2 headroom gate blocked before provider reads")

    progress = {"requests": 0, "protected_range_violation": 0}
    manifest_rows: list[dict[str, object]] = []
    coverage_counts: dict[str, int] = {}
    uploaded_bytes = 0
    uploaded_objects = 0
    verified_existing_objects = 0

    for profile, symbol, interval in iter_partitions(config):
        require_execution_window(config, now_ms=clock())
        prefix = _partition_prefix(config, symbol, interval)
        data_key = f"{prefix}/candles.parquet"
        receipt_key = f"{prefix}/receipt.json"
        existing_receipt = store.get_bytes_if_exists(receipt_key)
        if existing_receipt is not None:
            receipt = json.loads(existing_receipt)
            if (
                receipt.get("schema") != "pionex-validation-partition-receipt-v0.1"
                or receipt.get("config_sha256") != CONFIG_SHA256
                or receipt.get("symbol") != symbol
                or receipt.get("interval") != interval
                or receipt.get("provider") != "pionex_public_futures"
                or receipt.get("data_key") != data_key
            ):
                raise ValidationMaterializationRejected(f"existing partition receipt mismatch: {receipt_key}")
            store.get_bytes_verified(data_key, expected_sha256=str(receipt["data_sha256"]))
            verified_existing_objects += 2
            coverage = str(receipt["coverage_status"])
            coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1
            manifest_rows.append({
                "symbol": symbol,
                "interval": interval,
                "history_profile": profile,
                "asset_class": asset_class_for_symbol(config, symbol),
                "coverage_status": coverage,
                "rows": int(receipt["rows"]),
                "data_key": data_key,
                "data_sha256": receipt["data_sha256"],
                "receipt_key": receipt_key,
                "receipt_sha256": sha256_bytes(existing_receipt),
                "action": "VERIFY_EXISTING",
            })
            continue

        result = collect_partition(
            config,
            client,
            symbol=symbol,
            interval=interval,
            progress=progress,
            clock=clock,
        )
        parquet = candles_to_parquet(result.candles)
        if parquet_to_candles(parquet.payload) != list(result.candles):
            raise ValidationMaterializationRejected("Parquet round-trip mismatch")
        receipt = {
            "schema": "pionex-validation-partition-receipt-v0.1",
            "status": "PASS",
            "config_sha256": CONFIG_SHA256,
            "provider": "pionex_public_futures",
            "source_universe_run_id": config["source_universe"]["workflow_run_id"],
            "source_universe_artifact_digest": config["source_universe"]["artifact_digest"],
            "symbol": symbol,
            "asset_class": asset_class_for_symbol(config, symbol),
            "history_profile": profile_for_symbol(config, symbol),
            "interval": interval,
            "cutoff_exclusive_utc": config["cutoff_exclusive_utc"],
            **result.receipt_fields(),
            "data_key": data_key,
            "data_sha256": parquet.sha256,
            "data_bytes": len(parquet.payload),
            "provider_splicing_performed": False,
            "silent_interpolation_performed": False,
            "binance_data_used": False,
            "holdout_accessed": False,
            "training_authorized": False,
            "live_trading_authorized": False,
        }
        receipt_payload = json_bytes(receipt)
        planned = len(parquet.payload) + len(receipt_payload)
        if uploaded_bytes + planned > reservation:
            raise ValidationMaterializationRejected("actual validation-data writes exceeded planned run reservation")
        data_action = _put_or_verify(
            store,
            data_key,
            parquet.payload,
            content_type="application/vnd.apache.parquet",
            metadata={"provider": "pionex_public_futures", "role": "validation_candles", "version": "v0.1"},
        )
        receipt_action = _put_or_verify(
            store,
            receipt_key,
            receipt_payload,
            content_type="application/json",
            metadata={"provider": "pionex_public_futures", "role": "validation_receipt", "version": "v0.1"},
        )
        for action, size in ((data_action, len(parquet.payload)), (receipt_action, len(receipt_payload))):
            if action == "UPLOAD":
                uploaded_objects += 1
                uploaded_bytes += size
            else:
                verified_existing_objects += 1
        coverage = result.coverage_status
        coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1
        manifest_rows.append({
            "symbol": symbol,
            "interval": interval,
            "history_profile": profile,
            "asset_class": asset_class_for_symbol(config, symbol),
            "coverage_status": coverage,
            "rows": len(result.candles),
            "data_key": data_key,
            "data_sha256": parquet.sha256,
            "receipt_key": receipt_key,
            "receipt_sha256": sha256_bytes(receipt_payload),
            "action": "UPLOAD" if "UPLOAD" in {data_action, receipt_action} else "VERIFY_EXISTING",
        })

    expected_partitions = partition_count(config)
    if len(manifest_rows) != expected_partitions:
        raise ValidationMaterializationRejected("not all frozen validation partitions were materialized")
    if progress["protected_range_violation"]:
        raise ValidationMaterializationRejected("protected range violation observed; publication blocked")

    ending_bytes = current_bucket_bytes(store)
    if ending_bytes > hard_stop:
        raise ValidationMaterializationRejected("FREE-ONLY hard stop exceeded before manifest publication")

    manifest = {
        "schema": "pionex-validation-dataset-manifest-v0.1",
        "status": "PASS",
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "config_sha256": CONFIG_SHA256,
        "architecture": config["architecture"],
        "source_universe": config["source_universe"],
        "cutoff_exclusive_utc": config["cutoff_exclusive_utc"],
        "selected_market_count": 197,
        "partition_count": expected_partitions,
        "classification_counts": config["classification_overlay"]["class_counts"],
        "history_profile_counts": {name: len(value["symbols"]) for name, value in config["history_profiles"].items()},
        "coverage_counts": dict(sorted(coverage_counts.items())),
        "provider_requests": progress["requests"],
        "partitions": manifest_rows,
        "complete_197_market_multiyear_history_claimed": False,
        "core100_pionex_training_performed": False,
        "provider_splicing_performed": False,
        "silent_interpolation_performed": False,
        "replacement_holdout_accessed": False,
        "source_switch_authorized": False,
        "training_authorized": False,
        "model_promotion_authorized": False,
        "trade_plan_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }
    manifest_payload = json_bytes(manifest)
    manifest_key = f"{namespace}/runs/run={run_id}/manifest.json"
    manifest_action = _put_or_verify(
        store,
        manifest_key,
        manifest_payload,
        content_type="application/json",
        metadata={"provider": "pionex_public_futures", "role": "validation_manifest", "version": "v0.1"},
    )
    latest = {
        "schema": "pionex-validation-dataset-latest-v0.1",
        "status": "PASS",
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "config_sha256": CONFIG_SHA256,
        "manifest_key": manifest_key,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "partition_count": expected_partitions,
        "selected_market_count": 197,
        "cutoff_exclusive_utc": config["cutoff_exclusive_utc"],
    }
    latest_payload = json_bytes(latest)
    store.put_bytes(
        latest_key,
        latest_payload,
        content_type="application/json",
        metadata={"provider": "pionex_public_futures", "role": "latest_pointer", "version": "v0.1"},
    )
    if store.get_bytes_verified(latest_key, expected_sha256=sha256_bytes(latest_payload)) != latest_payload:
        raise ValidationMaterializationRejected("latest pointer readback mismatch")

    return {
        "status": "PASS",
        "stage": "PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_1",
        "run_id": run_id,
        "manifest_key": manifest_key,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "partition_count": expected_partitions,
        "selected_market_count": 197,
        "coverage_counts": dict(sorted(coverage_counts.items())),
        "provider_requests": progress["requests"],
        "r2_uploaded_objects": uploaded_objects + (1 if manifest_action == "UPLOAD" else 0) + 1,
        "r2_verified_existing_objects": verified_existing_objects + (1 if manifest_action != "UPLOAD" else 0),
        "r2_uploaded_partition_bytes": uploaded_bytes,
        "r2_latest_pointer_written_last": True,
        "complete_197_market_multiyear_history_claimed": False,
        "core100_pionex_training_performed": False,
        "holdout_accessed": False,
        "private_api_used": False,
        "source_switch_authorized": False,
        "training_authorized": False,
        "model_promotion_authorized": False,
        "trade_plan_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
        "r2_writes_performed": True,
    }


def main() -> int:
    from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output
    from crypto_autopilot.storage.r2 import R2Store

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = {
        "schema": "pionex-validation-materialization-run-report-v0.1",
        "status": "FAIL",
        "config_sha256": CONFIG_SHA256,
        "provider": "pionex_public_futures",
        "api_key_used": False,
        "private_api_used": False,
        "account_data_accessed": False,
        "raw_provider_payloads_persisted": False,
        "replacement_holdout_accessed": False,
        "training_authorized": False,
        "source_switch_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }
    try:
        run_id = require_github_main_dispatch()
        config = load_authority()

        def now() -> int:
            return int(time.time() * 1000)

        require_execution_window(config, now_ms=now())
        store = R2Store(
            account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
            bucket=os.environ["R2_BUCKET_NAME"],
            access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        )
        client = PionexPublicClient(
            timeout_seconds=float(config["materialization"]["request_timeout_seconds"]),
            requests_per_second=float(config["materialization"]["requests_per_second"]),
        )
        result = execute(config, store, client, run_id, clock=now)
        report = {**base, **result}
    except Exception as exc:
        reason = str(exc) if isinstance(exc, ValidationMaterializationRejected) else "runtime failure: " + type(exc).__name__
        report = {**base, "reason": reason}
        if isinstance(exc, ValidationMaterializationRejected) and exc.diagnostics:
            report["diagnostics"] = exc.diagnostics

    output = require_ephemeral_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {"PASS", "ALREADY_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())