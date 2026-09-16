#!/usr/bin/env python3
"""Materialize Pionex Validation Dataset V0.2 with native-1D weekly construction."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from crypto_autopilot.history.pionex_validation_materialization_v0_1 import (
    PartitionResult,
    ValidationMaterializationRejected,
    asset_class_for_symbol,
    iter_partitions,
    json_bytes,
    partition_count,
    profile_for_symbol,
    require_execution_window,
    sha256_bytes,
    validate_config,
)
from crypto_autopilot.history.pionex_validation_materialization_v0_2 import (
    collect_partition_v0_2,
    validate_overlay,
    weekly_from_native_daily,
)

import run_pionex_validation_materialization_v0_1 as v01_runner

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "config/pionex_validation_materialization_v0_2.json"
EXECUTION_AUTHORITY = ROOT / "research/receipts/pionex-validation-materialization-v0-2-execution-authority.json"
OVERLAY_SHA256 = "a45753c8b7d5236815e2ffe9e8ff5a6a17df523019dfef9570310a57d378cd4a"
BASE_CONFIG_SHA256 = v01_runner.CONFIG_SHA256


def load_design() -> tuple[dict, dict]:
    base = v01_runner.load_authority()
    payload = OVERLAY.read_bytes()
    if sha256_bytes(payload) != OVERLAY_SHA256:
        raise ValidationMaterializationRejected("V0.2 overlay bytes changed")
    overlay = json.loads(payload)
    validate_overlay(overlay)
    validate_config(base)
    return base, overlay


def require_execution_authority() -> dict:
    if not EXECUTION_AUTHORITY.exists():
        raise ValidationMaterializationRejected("V0.2 execution authority receipt is not present")
    receipt = json.loads(EXECUTION_AUTHORITY.read_bytes())
    expected = {
        "schema": "pionex-validation-materialization-v0.2-execution-authority",
        "status": "AUTHORIZED_AFTER_REVIEWED_MAIN_MERGE_MANUAL_ONLY",
        "base_config_sha256": BASE_CONFIG_SHA256,
        "overlay_sha256": OVERLAY_SHA256,
        "execution_performed_by_this_receipt": False,
        "holdout_access_authorized": False,
        "model_promotion_authorized": False,
        "source_switch_authorized": False,
        "training_authorized": False,
        "trade_plan_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }
    if receipt != expected:
        raise ValidationMaterializationRejected("V0.2 execution authority receipt mismatch")
    return receipt


def _partition_prefix(namespace: str, cutoff: str, symbol: str, interval: str) -> str:
    cutoff_day = cutoff.split("T", 1)[0]
    return f"{namespace.rstrip('/')}/cutoff={cutoff_day}/symbol={symbol}/interval={interval}"


def _put_or_verify(store, key: str, payload: bytes, *, content_type: str, metadata: dict[str, str]) -> str:
    return v01_runner._put_or_verify(
        store,
        key,
        payload,
        content_type=content_type,
        metadata=metadata,
    )


def _daily_result_from_receipt(receipt: dict, candles) -> PartitionResult:
    return PartitionResult(
        symbol=str(receipt["symbol"]),
        interval="1D",
        coverage_status=str(receipt["coverage_status"]),
        candles=tuple(candles),
        requests=int(receipt.get("requests", 0)),
        provider_error_type=receipt.get("provider_error_type"),
        provider_http_status=receipt.get("provider_http_status"),
    )


def execute(base: dict, overlay: dict, store, client, run_id: str, *, clock) -> dict:
    from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
    from crypto_autopilot.training.online_r2 import current_bucket_bytes

    validate_config(base)
    validate_overlay(overlay)
    require_execution_window(base, now_ms=clock())

    namespace = str(overlay["storage"]["namespace"]).rstrip("/")
    latest_key = f"{namespace}/latest.json"
    old_latest = store.get_bytes_if_exists(latest_key)
    if old_latest is not None:
        latest = json.loads(old_latest)
        if (
            latest.get("overlay_sha256") != OVERLAY_SHA256
            or latest.get("base_config_sha256") != BASE_CONFIG_SHA256
            or latest.get("status") != "PASS"
        ):
            raise ValidationMaterializationRejected("existing latest pointer does not match V0.2 authority")
        return {
            "status": "ALREADY_COMPLETE",
            "stage": "PIONEX_VALIDATION_DATASET_ALREADY_MATERIALIZED_V0_2",
            "manifest_key": latest.get("manifest_key"),
            "partition_count": latest.get("partition_count"),
            "provider_requests": 0,
            "r2_writes_performed": False,
        }

    current_bytes = current_bucket_bytes(store)
    hard_stop = int(base["storage"]["free_only_hard_stop_bytes"])
    reservation = int(base["storage"]["maximum_planned_run_bytes"])
    if current_bytes + reservation > hard_stop:
        raise ValidationMaterializationRejected("FREE-ONLY R2 headroom gate blocked before provider reads")

    progress = {"requests": 0, "protected_range_violation": 0}
    manifest_rows: list[dict[str, object]] = []
    coverage_counts: dict[str, int] = {}
    uploaded_bytes = 0
    uploaded_objects = 0
    verified_existing_objects = 0
    daily_cache: dict[str, tuple[PartitionResult, str, str]] = {}

    for profile, symbol, interval in iter_partitions(base):
        require_execution_window(base, now_ms=clock())
        prefix = _partition_prefix(namespace, str(base["cutoff_exclusive_utc"]), symbol, interval)
        data_key = f"{prefix}/candles.parquet"
        receipt_key = f"{prefix}/receipt.json"
        existing_receipt = store.get_bytes_if_exists(receipt_key)

        if existing_receipt is not None:
            receipt = json.loads(existing_receipt)
            if (
                receipt.get("schema") != "pionex-validation-partition-receipt-v0.2"
                or receipt.get("base_config_sha256") != BASE_CONFIG_SHA256
                or receipt.get("overlay_sha256") != OVERLAY_SHA256
                or receipt.get("symbol") != symbol
                or receipt.get("interval") != interval
                or receipt.get("provider") != "pionex_public_futures"
                or receipt.get("data_key") != data_key
            ):
                raise ValidationMaterializationRejected(f"existing V0.2 partition receipt mismatch: {receipt_key}")
            data_payload = store.get_bytes_verified(data_key, expected_sha256=str(receipt["data_sha256"]))
            verified_existing_objects += 2
            if interval == "1D":
                candles = parquet_to_candles(data_payload)
                daily_cache[symbol] = (
                    _daily_result_from_receipt(receipt, candles),
                    data_key,
                    str(receipt["data_sha256"]),
                )
            coverage = str(receipt["coverage_status"])
            coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1
            manifest_rows.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "physical_provider_interval": receipt["physical_provider_interval"],
                    "history_profile": profile,
                    "asset_class": asset_class_for_symbol(base, symbol),
                    "coverage_status": coverage,
                    "rows": int(receipt["rows"]),
                    "data_key": data_key,
                    "data_sha256": receipt["data_sha256"],
                    "receipt_key": receipt_key,
                    "receipt_sha256": sha256_bytes(existing_receipt),
                    "action": "VERIFY_EXISTING",
                }
            )
            continue

        try:
            if interval == "1W":
                source = daily_cache.get(symbol)
                if source is None:
                    raise ValidationMaterializationRejected(
                        "logical 1W requires the exact materialized native 1D source partition first"
                    )
                source_result, source_data_key, source_data_sha256 = source
                result = weekly_from_native_daily(
                    base,
                    symbol=symbol,
                    source_daily_result=source_result,
                )
                source_lineage = {
                    "source_daily_data_key": source_data_key,
                    "source_daily_data_sha256": source_data_sha256,
                    "source_daily_receipt_key": source_data_key.rsplit("/", 1)[0] + "/receipt.json",
                }
            else:
                result = collect_partition_v0_2(
                    base,
                    client,
                    symbol=symbol,
                    interval=interval,
                    progress=progress,
                    clock=clock,
                )
                source_lineage = {}
        except ValidationMaterializationRejected as exc:
            diagnostics = {
                **exc.diagnostics,
                "symbol": symbol,
                "interval": interval,
                "history_profile": profile,
                "provider_requests_before_failure": progress["requests"],
            }
            raise ValidationMaterializationRejected(str(exc), diagnostics=diagnostics) from None

        parquet = candles_to_parquet(result.candles)
        if parquet_to_candles(parquet.payload) != list(result.candles):
            raise ValidationMaterializationRejected("Parquet round-trip mismatch")

        receipt_fields = result.receipt_fields()
        receipt = {
            "schema": "pionex-validation-partition-receipt-v0.2",
            "status": "PASS",
            "base_config_sha256": BASE_CONFIG_SHA256,
            "overlay_sha256": OVERLAY_SHA256,
            "provider": "pionex_public_futures",
            "source_universe_run_id": base["source_universe"]["workflow_run_id"],
            "source_universe_artifact_digest": base["source_universe"]["artifact_digest"],
            "symbol": symbol,
            "asset_class": asset_class_for_symbol(base, symbol),
            "history_profile": profile_for_symbol(base, symbol),
            "interval": interval,
            "logical_interval": interval,
            "physical_provider_interval": "1D" if interval == "1W" else interval,
            "cutoff_exclusive_utc": base["cutoff_exclusive_utc"],
            **receipt_fields,
            **source_lineage,
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
            metadata={"provider": "pionex_public_futures", "role": "validation_candles", "version": "v0.2"},
        )
        receipt_action = _put_or_verify(
            store,
            receipt_key,
            receipt_payload,
            content_type="application/json",
            metadata={"provider": "pionex_public_futures", "role": "validation_receipt", "version": "v0.2"},
        )
        for action, size in ((data_action, len(parquet.payload)), (receipt_action, len(receipt_payload))):
            if action == "UPLOAD":
                uploaded_objects += 1
                uploaded_bytes += size
            else:
                verified_existing_objects += 1

        if interval == "1D":
            daily_cache[symbol] = (result, data_key, parquet.sha256)

        coverage = result.coverage_status
        coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1
        manifest_rows.append(
            {
                "symbol": symbol,
                "interval": interval,
                "physical_provider_interval": "1D" if interval == "1W" else interval,
                "history_profile": profile,
                "asset_class": asset_class_for_symbol(base, symbol),
                "coverage_status": coverage,
                "rows": len(result.candles),
                "data_key": data_key,
                "data_sha256": parquet.sha256,
                "receipt_key": receipt_key,
                "receipt_sha256": sha256_bytes(receipt_payload),
                "action": "UPLOAD" if "UPLOAD" in {data_action, receipt_action} else "VERIFY_EXISTING",
            }
        )

    expected_partitions = partition_count(base)
    if len(manifest_rows) != expected_partitions:
        raise ValidationMaterializationRejected("not all frozen validation partitions were materialized")
    if progress["protected_range_violation"]:
        raise ValidationMaterializationRejected("protected range violation observed; publication blocked")

    ending_bytes = current_bucket_bytes(store)
    if ending_bytes > hard_stop:
        raise ValidationMaterializationRejected("FREE-ONLY hard stop exceeded before manifest publication")

    manifest = {
        "schema": "pionex-validation-dataset-manifest-v0.2",
        "status": "PASS",
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "base_config_sha256": BASE_CONFIG_SHA256,
        "overlay_sha256": OVERLAY_SHA256,
        "architecture": base["architecture"],
        "source_universe": base["source_universe"],
        "weekly_materialization": overlay["weekly_materialization"],
        "cutoff_exclusive_utc": base["cutoff_exclusive_utc"],
        "selected_market_count": 197,
        "partition_count": expected_partitions,
        "classification_counts": base["classification_overlay"]["class_counts"],
        "history_profile_counts": {
            name: len(value["symbols"]) for name, value in base["history_profiles"].items()
        },
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
        metadata={"provider": "pionex_public_futures", "role": "validation_manifest", "version": "v0.2"},
    )

    latest = {
        "schema": "pionex-validation-dataset-latest-v0.2",
        "status": "PASS",
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "base_config_sha256": BASE_CONFIG_SHA256,
        "overlay_sha256": OVERLAY_SHA256,
        "manifest_key": manifest_key,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "partition_count": expected_partitions,
        "selected_market_count": 197,
        "cutoff_exclusive_utc": base["cutoff_exclusive_utc"],
    }
    latest_payload = json_bytes(latest)
    store.put_bytes(
        latest_key,
        latest_payload,
        content_type="application/json",
        metadata={"provider": "pionex_public_futures", "role": "latest_pointer", "version": "v0.2"},
    )
    if store.get_bytes_verified(latest_key, expected_sha256=sha256_bytes(latest_payload)) != latest_payload:
        raise ValidationMaterializationRejected("latest pointer readback mismatch")

    return {
        "status": "PASS",
        "stage": "PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_2",
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
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    base_report = {
        "schema": "pionex-validation-materialization-run-report-v0.2",
        "status": "FAIL",
        "base_config_sha256": BASE_CONFIG_SHA256,
        "overlay_sha256": OVERLAY_SHA256,
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
        base, overlay = load_design()
        if args.preflight_only:
            report = {
                **base_report,
                "status": "BLOCKED",
                "stage": "V0_2_IMPLEMENTED_EXECUTION_AUTHORITY_REQUIRED",
                "execution_authorized": False,
                "r2_writes_performed": False,
            }
        else:
            from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
            from crypto_autopilot.storage.r2 import R2Store

            require_execution_authority()
            run_id = v01_runner.require_github_main_dispatch()

            def now() -> int:
                return int(time.time() * 1000)

            require_execution_window(base, now_ms=now())
            store = R2Store(
                account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
                bucket=os.environ["R2_BUCKET_NAME"],
                access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            )
            client = PionexPublicClient(
                timeout_seconds=float(base["materialization"]["request_timeout_seconds"]),
                requests_per_second=float(base["materialization"]["requests_per_second"]),
            )
            report = {**base_report, **execute(base, overlay, store, client, run_id, clock=now)}
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, ValidationMaterializationRejected)
            else "runtime failure: " + type(exc).__name__
        )
        report = {**base_report, "reason": reason}
        if isinstance(exc, ValidationMaterializationRejected) and exc.diagnostics:
            report["diagnostics"] = exc.diagnostics

    output = require_ephemeral_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    if args.preflight_only and report["status"] == "BLOCKED":
        return 0
    return 0 if report["status"] in {"PASS", "ALREADY_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())