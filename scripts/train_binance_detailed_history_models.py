#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_autopilot.history.detailed import (
    DetailedHistoryAuthorityError,
    canonical_json_bytes,
    load_authority_pair,
    require_execution_window,
    sha256_bytes,
    validate_catalog,
)
from crypto_autopilot.training.detailed import (
    IntradayExample,
    bound_examples,
    build_intraday_examples,
    run_intraday_training,
)
from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.training.online_r2 import current_bucket_bytes
from crypto_autopilot.storage.parquet import parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-24-binance-usdm-detailed-history-v0-1-1-bounded-authority.json"
)
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def create_store() -> R2Store:
    return R2Store(
        account_id=required("CLOUDFLARE_ACCOUNT_ID"),
        bucket=required("R2_BUCKET_NAME"),
        access_key_id=required("R2_ACCESS_KEY_ID"),
        secret_access_key=required("R2_SECRET_ACCESS_KEY"),
    )


def load_dataset_index(
    store: R2Store, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], str]:
    storage = config["storage"]
    latest_payload = store.get_bytes_if_exists(storage["catalog_latest_pointer_key"])
    state_payload = store.get_bytes_if_exists(storage["backfill_state_key"])
    if latest_payload is None or state_payload is None:
        raise DetailedHistoryAuthorityError("detailed-history catalog/backfill state is missing")
    latest = json.loads(latest_payload)
    state = json.loads(state_payload)
    if (
        latest.get("schema") != "binance-usdm-detailed-history-catalog-latest-v0.1"
        or state.get("schema") != "binance-usdm-detailed-history-backfill-state-v0.1"
        or state.get("status") != "COMPLETE"
        or state.get("catalog_key") != latest.get("catalog_key")
        or state.get("catalog_sha256") != latest.get("catalog_sha256")
        or state.get("holdout_accessed") is not False
    ):
        raise DetailedHistoryAuthorityError("detailed-history dataset is not complete and bound")
    catalog_payload = store.get_bytes_verified(
        latest["catalog_key"], expected_sha256=latest["catalog_sha256"]
    )
    catalog = json.loads(catalog_payload)
    validate_catalog(catalog, config=config)
    completed = state.get("completed_shards")
    if not isinstance(completed, list) or len(completed) != int(state["shard_count"]):
        raise DetailedHistoryAuthorityError("detailed-history completed shard set is incomplete")
    object_records: list[dict[str, Any]] = []
    receipt_bindings = []
    for item in sorted(completed, key=lambda row: int(row["shard_index"])):
        payload = store.get_bytes_verified(
            item["receipt_key"], expected_sha256=item["receipt_sha256"]
        )
        receipt = json.loads(payload)
        if (
            receipt.get("schema") != "binance-usdm-detailed-history-shard-receipt-v0.1"
            or receipt.get("status") != "PASS"
            or receipt.get("catalog_sha256") != latest["catalog_sha256"]
            or receipt.get("authority", {}).get("holdout_accessed") is not False
        ):
            raise DetailedHistoryAuthorityError("detailed-history shard receipt mismatch")
        object_records.extend(receipt["objects"])
        receipt_bindings.append(
            {
                "shard_index": item["shard_index"],
                "receipt_key": item["receipt_key"],
                "receipt_sha256": item["receipt_sha256"],
            }
        )
    keys = [str(item["r2_key"]) for item in object_records]
    if len(keys) != len(set(keys)) or len(keys) != int(state["total_partition_objects"]):
        raise DetailedHistoryAuthorityError("detailed-history partition index mismatch")
    fingerprint = sha256_bytes(
        canonical_json_bytes(
            {
                "catalog_key": latest["catalog_key"],
                "catalog_sha256": latest["catalog_sha256"],
                "shard_receipts": receipt_bindings,
            }
        )
    )
    return catalog, state, object_records, fingerprint


def _period_ordinal(period: str) -> int:
    year, month = (int(value) for value in period.split("-", 1))
    return year * 12 + month


def _contiguous_period_segments(periods: list[str]) -> list[list[str]]:
    ordered = sorted(set(periods))
    output: list[list[str]] = []
    current: list[str] = []
    for period in ordered:
        if current and _period_ordinal(period) != _period_ordinal(current[-1]) + 1:
            output.append(current)
            current = []
        current.append(period)
    if current:
        output.append(current)
    return output


def build_examples_from_r2(
    store: R2Store,
    *,
    catalog: dict[str, Any],
    object_records: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[IntradayExample]:
    catalog_by_symbol = {str(item["symbol"]): item for item in catalog["markets"]}
    records_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in object_records:
        if (
            record.get("provider") != "binance_usdm"
            or record.get("delivery") != "binance_vision"
            or record.get("audit_ok") is not True
            or str(record.get("symbol")) not in catalog_by_symbol
        ):
            raise DetailedHistoryAuthorityError("detailed-history training object contract mismatch")
        records_by_symbol[str(record["symbol"])].append(record)

    training = config["training"]
    base_cost = next(item for item in training["cost_scenarios"] if item["name"] == "base")
    label_cost = 2.0 * (
        float(base_cost["fee_bps_per_side"]) + float(base_cost["slippage_bps_per_side"])
    )
    all_examples: list[IntradayExample] = []
    for symbol in sorted(records_by_symbol):
        records = records_by_symbol[symbol]
        by_interval_period = {
            (str(item["interval"]), str(item["period"])): item for item in records
        }
        periods_by_interval = {
            interval: {
                period for observed_interval, period in by_interval_period if observed_interval == interval
            }
            for interval in ("15m", "1h", "4h")
        }
        common_periods = sorted(set.intersection(*periods_by_interval.values()))
        symbol_examples: list[IntradayExample] = []
        for segment in _contiguous_period_segments(common_periods):
            candles_by_interval = {}
            for interval in ("15m", "1h", "4h"):
                candles = []
                for period in segment:
                    record = by_interval_period[(interval, period)]
                    payload = store.get_bytes_verified(
                        record["r2_key"], expected_sha256=record["r2_sha256"]
                    )
                    restored = parquet_to_candles(payload)
                    if len(restored) != int(record["source_rows"]):
                        raise DetailedHistoryAuthorityError("detailed-history Parquet row mismatch")
                    candles.extend(restored)
                candles_by_interval[interval] = tuple(candles)
            symbol_examples.extend(
                build_intraday_examples(
                    symbol=symbol,
                    asset_class=str(catalog_by_symbol[symbol]["asset_class"]),
                    candles_by_interval=candles_by_interval,
                    sample_stride_15m_bars=int(training["sample_stride_15m_bars"]),
                    forward_horizon_15m_bars=int(training["forward_horizon_15m_bars"]),
                    label_cost_bps_round_trip=label_cost,
                )
            )
        all_examples.extend(
            bound_examples(symbol_examples, int(training["maximum_examples_per_symbol"]))
        )
    return bound_examples(all_examples, int(training["maximum_total_examples"]))


def put_immutable(
    store: R2Store,
    *,
    key: str,
    payload: bytes,
    role: str,
) -> dict[str, Any]:
    existing = store.get_bytes_if_exists(key)
    if existing is not None and existing != payload:
        raise DetailedHistoryAuthorityError(f"immutable intraday training conflict: {key}")
    if existing is None:
        receipt = store.put_bytes(
            key,
            payload,
            content_type="application/json",
            metadata={"provider": "binance_usdm", "role": role, "version": "v0.1"},
        )
        action = "UPLOAD"
        sha = receipt.sha256
        size = receipt.bytes
    else:
        action = "VERIFY_EXISTING"
        sha = hashlib.sha256(existing).hexdigest()
        size = len(existing)
    restored = store.get_bytes_verified(key, expected_sha256=sha)
    if restored != payload:
        raise DetailedHistoryAuthorityError("intraday training R2 round trip mismatch")
    return {"key": key, "bytes": size, "sha256": sha, "action": action}


def publish_training(
    store: R2Store,
    *,
    config: dict[str, Any],
    model: dict[str, Any],
    metrics: dict[str, Any],
    dataset_fingerprint: str,
    run_id: str,
    generated_at_utc: str,
) -> dict[str, Any]:
    namespace = config["storage"]["training_namespace"].rstrip("/")
    run_prefix = f"{namespace}/runs/run={run_id}"
    model_payload = canonical_json_bytes(model)
    metrics_payload = canonical_json_bytes(metrics)
    manifest = {
        "schema": "binance-usdm-intraday-research-training-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "model_quality_gate": metrics["model_quality_gate"],
        "objects": [
            {
                "role": "model",
                "key": f"{run_prefix}/model.json",
                "bytes": len(model_payload),
                "sha256": sha256_bytes(model_payload),
            },
            {
                "role": "metrics",
                "key": f"{run_prefix}/metrics.json",
                "bytes": len(metrics_payload),
                "sha256": sha256_bytes(metrics_payload),
            },
        ],
        "authority": model["authority"],
    }
    manifest_payload = canonical_json_bytes(manifest)
    latest = {
        "schema": "binance-usdm-intraday-research-training-latest-v0.1",
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "manifest_key": f"{run_prefix}/manifest.json",
        "manifest_sha256": sha256_bytes(manifest_payload),
        "model_key": f"{run_prefix}/model.json",
        "model_sha256": sha256_bytes(model_payload),
        "metrics_key": f"{run_prefix}/metrics.json",
        "metrics_sha256": sha256_bytes(metrics_payload),
        "model_quality_gate": metrics["model_quality_gate"],
    }
    latest_payload = canonical_json_bytes(latest)
    current = current_bucket_bytes(store)
    planned = len(model_payload) + len(metrics_payload) + len(manifest_payload) + len(latest_payload)
    if current + planned > int(config["storage"]["free_only_hard_stop_bytes"]):
        raise DetailedHistoryAuthorityError("R2 training evidence headroom gate blocked")
    records = [
        put_immutable(store, key=f"{run_prefix}/model.json", payload=model_payload, role="model"),
        put_immutable(store, key=f"{run_prefix}/metrics.json", payload=metrics_payload, role="metrics"),
        put_immutable(
            store,
            key=f"{run_prefix}/manifest.json",
            payload=manifest_payload,
            role="manifest",
        ),
    ]
    pointer = store.put_bytes(
        f"{namespace}/latest.json",
        latest_payload,
        content_type="application/json",
        metadata={"provider": "binance_usdm", "role": "training-latest", "version": "v0.1"},
    )
    restored = store.get_bytes_verified(
        f"{namespace}/latest.json", expected_sha256=pointer.sha256
    )
    if restored != latest_payload:
        raise DetailedHistoryAuthorityError("training latest pointer round trip mismatch")
    return {
        "status": "PASS",
        "stage": "BINANCE_USDM_INTRADAY_RESEARCH_TRAINING_PUBLISHED_V0_1",
        "model_quality_gate": metrics["model_quality_gate"],
        "example_count": metrics["example_count"],
        "symbol_count": metrics["symbol_count"],
        "objects": records,
        "latest_pointer_written_last": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train the bounded intraday research model from completed R2 detailed history."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now-utc")
    args = parser.parse_args()
    output = require_ephemeral_output(args.output)
    if not SAFE_RUN_ID.fullmatch(args.run_id):
        raise ValueError("run id must be a safe 1-96 character object-key component")
    config, _authority, _config_bytes = load_authority_pair(args.config, args.authority)
    observed = (
        datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
        if args.now_utc
        else datetime.now(UTC)
    )
    generated_at = observed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    try:
        require_execution_window(config, observed_at=observed, operation="training")
    except DetailedHistoryAuthorityError as exc:
        if "blocked until the V0.10 window has ended" not in str(exc):
            raise
        report = {
            "status": "SKIPPED",
            "stage": "DETAILED_TRAINING_NOT_BEFORE_GUARD",
            "observed_at_utc": generated_at,
            "reason": str(exc),
            "provider_requests_performed": 0,
            "r2_access_performed": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(report))
        print(json.dumps(report, sort_keys=True))
        return 0
    store = create_store()
    try:
        catalog, state, object_records, fingerprint = load_dataset_index(store, config)
    except DetailedHistoryAuthorityError as exc:
        if str(exc) not in {
            "detailed-history catalog/backfill state is missing",
            "detailed-history dataset is not complete and bound",
        }:
            raise
        report = {
            "status": "SKIPPED",
            "stage": "DETAILED_HISTORY_DATASET_NOT_READY",
            "observed_at_utc": generated_at,
            "reason": str(exc),
            "provider_requests_performed": 0,
            "r2_writes_performed": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(report))
        print(json.dumps(report, sort_keys=True))
        return 0
    examples = build_examples_from_r2(
        store,
        catalog=catalog,
        object_records=object_records,
        config=config,
    )
    model, metrics = run_intraday_training(
        examples,
        config=config,
        dataset_fingerprint=fingerprint,
        generated_at_utc=generated_at,
    )
    result = publish_training(
        store,
        config=config,
        model=model,
        metrics=metrics,
        dataset_fingerprint=fingerprint,
        run_id=args.run_id,
        generated_at_utc=generated_at,
    )
    report = {
        **result,
        "observed_at_utc": generated_at,
        "dataset_fingerprint": fingerprint,
        "dataset_rows": state["total_rows"],
        "dataset_partition_objects": state["total_partition_objects"],
        "authority": model["authority"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
