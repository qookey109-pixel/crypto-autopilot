from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from collections.abc import Callable

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pyarrow as pa

from crypto_autopilot.online_r2_training import (
    build_online_objects,
    json_bytes,
    publish_online_objects,
)
from crypto_autopilot.ephemeral_storage import require_ephemeral_output
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training_quality import (
    TrainingQualityError,
    V0_3_BASELINE_EVIDENCE_SHA256,
    load_v0_3_bootstrap_baseline,
    load_v0_5_authority_pair,
    validate_catalog_quality,
    validate_dataset_receipt_quality,
    validate_metrics_contract,
    validate_model_contract,
    validate_weekly_review_contract,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_PARQUET_COLUMNS = (
    "provider",
    "market_type",
    "asset_class",
    "classification_method",
    "classification_confidence",
    "base_asset",
    "quote_asset",
    "symbol",
    "interval",
    "audit_ok",
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "base_volume",
    "quote_volume",
    "trade_count",
)
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_MODES = {
    "local": "LOCAL_DRY_RUN",
    "schedule": "SCHEDULED_TRAINING",
    "workflow_dispatch": "MANUAL_TRAINING",
}


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_execution_route(
    *, event_name: str, activation_mode: str, dry_run: bool
) -> dict[str, object]:
    expected_mode = _EXECUTION_MODES.get(event_name)
    if expected_mode is None:
        raise TrainingQualityError("unsupported V0.5 weekly workflow event")
    if activation_mode != expected_mode:
        raise TrainingQualityError("V0.5 weekly event and activation mode mismatch")
    if event_name == "local" and not dry_run:
        raise TrainingQualityError("local V0.5 weekly execution must be a dry run")
    return {
        "event_name": event_name,
        "activation_mode": activation_mode,
        "manual_execution": event_name == "workflow_dispatch",
    }


def _provider_read_stop_time_ms(config: dict[str, object]) -> int:
    schedule = config.get("schedule")
    if not isinstance(schedule, dict):
        raise TrainingQualityError("V0.5 online write schedule is missing")
    stop = datetime.fromisoformat(
        str(schedule["provider_read_stop_utc"]).replace("Z", "+00:00")
    )
    return int(stop.timestamp() * 1000)


def _expected_last_complete_day_open_time_ms(observed_at: datetime) -> int:
    if observed_at.tzinfo is None:
        raise TrainingQualityError("V0.5 observation clock must be timezone-aware")
    observed_utc = observed_at.astimezone(UTC)
    last_complete_day = datetime(
        observed_utc.year,
        observed_utc.month,
        observed_utc.day,
        tzinfo=UTC,
    ) - timedelta(days=1)
    return int(last_complete_day.timestamp() * 1000)


def _require_online_write_window(
    config: dict[str, object], *, observed_at: datetime | None = None
) -> None:
    stop_time_ms = _provider_read_stop_time_ms(config)
    observed = utc_now() if observed_at is None else observed_at
    if int(observed.astimezone(UTC).timestamp() * 1000) >= stop_time_ms:
        raise TrainingQualityError("V0.5 online write window is closed")


def _previous_dataset_receipt(
    store: R2Store,
    config: dict[str, object],
    *,
    governance_contract: dict[str, object],
    before_access: Callable[[], None] | None = None,
) -> tuple[dict[str, object], dict[str, object]] | None:
    storage = config.get("storage")
    if not isinstance(storage, dict) or storage.get("schema_version") != "v0.5":
        raise TrainingQualityError("previous dataset lookup requires V0.5 storage config")
    training_namespace = str(storage.get("training_namespace") or "").rstrip("/")
    dataset_namespace = str(storage.get("dataset_runs_namespace") or "").rstrip("/")
    latest_key = str(storage.get("latest_training_pointer_key") or "")
    if latest_key != f"{training_namespace}/latest.json":
        raise TrainingQualityError("training latest pointer is outside the V0.5 namespace")
    if before_access is not None:
        before_access()
    latest_payload = store.get_bytes_if_exists(latest_key)
    if latest_payload is None:
        return None
    latest = json.loads(latest_payload)
    if (
        not isinstance(latest, dict)
        or latest.get("schema") != "binance-spot-r2-automated-training-latest-v0.5"
        or latest.get("provider") != "binance_spot"
    ):
        raise TrainingQualityError("previous training latest pointer contract mismatch")
    previous_governance = latest.get("governance")
    if (
        not isinstance(previous_governance, dict)
        or previous_governance.get("config") != governance_contract
        or not isinstance(previous_governance.get("comparison_baseline"), dict)
        or latest.get("governance_sha256")
        != hashlib.sha256(json_bytes(previous_governance)).hexdigest()
    ):
        raise TrainingQualityError("previous training governance evidence mismatch")
    run_id = latest.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        raise TrainingQualityError("previous training run id is invalid")
    catalog_key = latest.get("catalog_key")
    expected_catalog_key = f"{dataset_namespace}/run={run_id}/market-catalog.json"
    if catalog_key != expected_catalog_key:
        raise TrainingQualityError("previous catalog key is outside its namespace")
    catalog_sha256 = latest.get("catalog_sha256")
    if not isinstance(catalog_sha256, str) or not _SHA256_RE.fullmatch(catalog_sha256):
        raise TrainingQualityError("previous catalog SHA-256 is invalid")
    dataset_key = latest.get("dataset_key")
    expected_dataset_key = f"{dataset_namespace}/run={run_id}/binance-spot-1d.parquet"
    if dataset_key != expected_dataset_key:
        raise TrainingQualityError("previous dataset key is outside its namespace")
    dataset_sha256 = latest.get("dataset_sha256")
    if not isinstance(dataset_sha256, str) or not _SHA256_RE.fullmatch(dataset_sha256):
        raise TrainingQualityError("previous dataset SHA-256 is invalid")
    receipt_key = latest.get("dataset_receipt_key")
    if receipt_key != f"{dataset_namespace}/run={run_id}/dataset-receipt.json":
        raise TrainingQualityError("previous dataset receipt key is outside its namespace")
    receipt_sha256 = latest.get("dataset_receipt_sha256")
    if not isinstance(receipt_sha256, str) or not _SHA256_RE.fullmatch(receipt_sha256):
        raise TrainingQualityError("previous dataset receipt SHA-256 is invalid")
    if before_access is not None:
        before_access()
    catalog_payload = store.get_bytes_verified(
        catalog_key, expected_sha256=catalog_sha256
    )
    if hashlib.sha256(catalog_payload).hexdigest() != catalog_sha256:
        raise TrainingQualityError("previous catalog SHA-256 mismatch")
    previous_catalog = json.loads(catalog_payload)
    validate_catalog_quality(previous_catalog, policy=config["data_quality"])
    if before_access is not None:
        before_access()
    payload = store.get_bytes_verified(receipt_key, expected_sha256=receipt_sha256)
    if hashlib.sha256(payload).hexdigest() != receipt_sha256:
        raise TrainingQualityError("previous dataset receipt SHA-256 mismatch")
    receipt = json.loads(payload)
    if not isinstance(receipt, dict):
        raise TrainingQualityError("previous dataset receipt contract mismatch")
    parquet_binding = receipt.get("parquet")
    if not isinstance(parquet_binding, dict):
        raise TrainingQualityError("previous dataset receipt Parquet binding is missing")
    validate_dataset_receipt_quality(
        receipt,
        catalog=previous_catalog,
        policy=config["data_quality"],
        expected_catalog_sha256=catalog_sha256,
        expected_catalog_bytes=len(catalog_payload),
        expected_dataset_sha256=dataset_sha256,
        expected_dataset_bytes=parquet_binding.get("bytes"),
        expected_last_open_time_ms=None,
        provider_read_stop_time_ms=_provider_read_stop_time_ms(config),
    )
    return receipt, {
        "source": "PREVIOUS_V0_5_DATASET_RECEIPT",
        "reference": receipt_key,
        "sha256": receipt_sha256,
        "market_count_requested": receipt.get("market_count_requested"),
        "market_count_audited": receipt.get("market_count_audited"),
        "row_count": receipt.get("row_count"),
        "bootstrap_used": False,
    }


def _parquet_contract(
    dataset_path: Path,
    *,
    catalog: dict[str, object],
    receipt: dict[str, object],
    provider_read_stop_time_ms: int,
) -> dict[str, object]:
    schema = pq.read_schema(dataset_path)
    if tuple(schema.names) != _PARQUET_COLUMNS:
        raise TrainingQualityError("Parquet column contract mismatch")
    string_columns = _PARQUET_COLUMNS[:9]
    floating_columns = (
        "open",
        "high",
        "low",
        "close",
        "base_volume",
        "quote_volume",
    )
    if (
        any(not pa.types.is_string(schema.field(name).type) for name in string_columns)
        or not pa.types.is_boolean(schema.field("audit_ok").type)
        or not pa.types.is_integer(schema.field("open_time_ms").type)
        or any(
            not pa.types.is_floating(schema.field(name).type)
            for name in floating_columns
        )
        or not pa.types.is_integer(schema.field("trade_count").type)
    ):
        raise TrainingQualityError("Parquet physical type contract mismatch")
    table = pq.read_table(dataset_path, columns=list(_PARQUET_COLUMNS))
    if any(table[name].null_count for name in _PARQUET_COLUMNS):
        raise TrainingQualityError("Parquet contract forbids null values")
    if table.num_rows != receipt.get("row_count"):
        raise TrainingQualityError("Parquet row count does not match dataset receipt")

    def all_true(values: object) -> bool:
        result = pc.all(values).as_py()
        return result is True

    if any(
        not all_true(pc.is_finite(table[name])) for name in floating_columns
    ):
        raise TrainingQualityError("Parquet numeric values must be finite")
    zero = pa.scalar(0.0)
    if (
        any(
            not all_true(pc.greater(table[name], zero))
            for name in ("open", "high", "low", "close")
        )
        or any(
            not all_true(pc.greater_equal(table[name], zero))
            for name in ("base_volume", "quote_volume")
        )
        or not all_true(pc.greater_equal(table["trade_count"], pa.scalar(0)))
        or not all_true(pc.greater_equal(table["high"], table["open"]))
        or not all_true(pc.greater_equal(table["high"], table["close"]))
        or not all_true(pc.greater_equal(table["high"], table["low"]))
        or not all_true(pc.less_equal(table["low"], table["open"]))
        or not all_true(pc.less_equal(table["low"], table["close"]))
    ):
        raise TrainingQualityError("Parquet OHLCV values violate market-data bounds")

    def unique_values(name: str) -> set[object]:
        return set(pc.unique(table[name]).to_pylist())

    if unique_values("provider") != {"binance_spot"}:
        raise TrainingQualityError("Parquet provider contract mismatch")
    if unique_values("market_type") != {"spot"} or unique_values("interval") != {"1d"}:
        raise TrainingQualityError("Parquet market type or interval contract mismatch")
    symbols = unique_values("symbol")
    catalog_by_symbol = {
        item["symbol"]: item for item in catalog["markets"] if isinstance(item, dict)
    }
    catalog_symbols = set(catalog_by_symbol)
    if (
        not symbols.issubset(catalog_symbols)
        or len(symbols) != receipt.get("market_count_with_rows")
    ):
        raise TrainingQualityError("Parquet symbols do not match dataset receipt and catalog")
    metadata_fields = (
        "symbol",
        "base_asset",
        "quote_asset",
        "asset_class",
        "classification_method",
        "classification_confidence",
    )
    metadata_rows = (
        table.select([*metadata_fields, "open_time_ms"])
        .group_by(list(metadata_fields))
        .aggregate([("open_time_ms", "count")])
        .to_pylist()
    )
    if len(metadata_rows) != len(symbols):
        raise TrainingQualityError("Parquet market metadata changes within a series")
    for item in metadata_rows:
        market = catalog_by_symbol[item["symbol"]]
        if any(item[field] != market[field] for field in metadata_fields[1:]):
            raise TrainingQualityError(
                f"Parquet market metadata does not match catalog: {item['symbol']}"
            )
    audited_symbols = set(
        pc.unique(table.filter(pc.equal(table["audit_ok"], True))["symbol"]).to_pylist()
    )
    failed_symbols = set(
        pc.unique(table.filter(pc.equal(table["audit_ok"], False))["symbol"]).to_pylist()
    )
    if audited_symbols & failed_symbols:
        raise TrainingQualityError("Parquet audit flag changes within a market series")
    audit_evidence = receipt["market_audit_evidence"]
    expected_audited = {
        symbol for symbol in symbols if audit_evidence[symbol].get("audit_ok") is True
    }
    if (
        audited_symbols != expected_audited
        or failed_symbols != set(receipt["audit_failures"])
        or audited_symbols | failed_symbols != symbols
    ):
        raise TrainingQualityError("Parquet audit flags do not match dataset receipt")
    coverage = (
        table.select(["symbol", "open_time_ms"])
        .group_by("symbol")
        .aggregate(
            [
                ("open_time_ms", "min"),
                ("open_time_ms", "max"),
                ("open_time_ms", "count"),
                ("open_time_ms", "count_distinct"),
            ]
        )
        .to_pylist()
    )
    day_ms = 86_400_000
    for item in coverage:
        symbol = item["symbol"]
        first_open = item["open_time_ms_min"]
        last_open = item["open_time_ms_max"]
        if (
            audit_evidence[symbol].get("actual_first_open_time_ms")
            != first_open
            or audit_evidence[symbol].get("actual_last_open_time_ms")
            != last_open
        ):
            raise TrainingQualityError(
                f"Parquet tail does not match dataset receipt: {symbol}"
            )
        if (
            isinstance(first_open, bool)
            or isinstance(last_open, bool)
            or not isinstance(first_open, int)
            or not isinstance(last_open, int)
            or first_open % day_ms != 0
            or last_open % day_ms != 0
            or last_open >= provider_read_stop_time_ms
        ):
            raise TrainingQualityError(
                f"Parquet daily coverage crossed the provider boundary: {symbol}"
            )
        row_count = item["open_time_ms_count"]
        distinct_count = item["open_time_ms_count_distinct"]
        expected_count = (last_open - first_open) // day_ms + 1
        if symbol in audited_symbols and (
            row_count != distinct_count or distinct_count != expected_count
        ):
            raise TrainingQualityError(
                f"Parquet daily coverage contains gaps or duplicates: {symbol}"
            )
    return {
        "status": "PASS",
        "row_count": table.num_rows,
        "market_count_with_rows": len(symbols),
        "market_count_audited": len(audited_symbols),
        "provider": "binance_spot",
        "interval": "1d",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Binance Spot dataset and research model to Cloudflare R2")
    parser.add_argument("--config", default="config/binance_spot_r2_training_governance_v0_5.json")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--dataset-receipt", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--weekly-review")
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument(
        "--event-name",
        default=os.getenv("GITHUB_EVENT_NAME") or "local",
    )
    parser.add_argument(
        "--activation-mode",
        default=os.getenv("V0_5_WEEKLY_ACTIVATION_MODE") or "LOCAL_DRY_RUN",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    output = require_ephemeral_output(args.output)

    config_path = Path(args.config)
    config_payload = config_path.read_bytes()
    config = json.loads(config_payload)
    _, governance_contract = load_v0_5_authority_pair(
        config,
        config_path=config_path,
        config_payload=config_payload,
        repository_root=REPOSITORY_ROOT,
    )
    execution_route = _validate_execution_route(
        event_name=args.event_name,
        activation_mode=args.activation_mode,
        dry_run=args.dry_run,
    )
    bootstrap_baseline = load_v0_3_bootstrap_baseline(
        config,
        repository_root=REPOSITORY_ROOT,
    )
    observed_at = utc_now()
    provider_read_stop_time_ms = _provider_read_stop_time_ms(config)
    expected_last_open_time_ms = _expected_last_complete_day_open_time_ms(observed_at)
    provider_read_start_time_ms = int(
        datetime.fromisoformat(
            str(config["source"]["start_utc"]).replace("Z", "+00:00")
        ).timestamp()
        * 1000
    )

    payloads = {
        name: Path(path).read_bytes()
        for name, path in (
            ("catalog", args.catalog),
            ("dataset", args.dataset),
            ("dataset_receipt", args.dataset_receipt),
            ("model", args.model),
            ("metrics", args.metrics),
        )
    }
    if args.weekly_review:
        payloads["weekly_review"] = Path(args.weekly_review).read_bytes()
    catalog = json.loads(payloads["catalog"])
    dataset_receipt = json.loads(payloads["dataset_receipt"])
    model = json.loads(payloads["model"])
    metrics = json.loads(payloads["metrics"])
    schema_version = str(config["storage"]["schema_version"])
    dataset_quality = None
    weekly_review_contract = None
    if schema_version != "v0.5":
        raise RuntimeError("only the current V0.5 R2 namespace is executable")
    policy = config["data_quality"]
    validate_catalog_quality(catalog, policy=policy)
    actual_catalog_sha = hashlib.sha256(payloads["catalog"]).hexdigest()
    actual_data_sha = hashlib.sha256(payloads["dataset"]).hexdigest()
    dataset_quality = validate_dataset_receipt_quality(
        dataset_receipt,
        catalog=catalog,
        policy=policy,
        expected_catalog_sha256=actual_catalog_sha,
        expected_catalog_bytes=len(payloads["catalog"]),
        expected_dataset_sha256=actual_data_sha,
        expected_dataset_bytes=len(payloads["dataset"]),
        expected_last_open_time_ms=expected_last_open_time_ms,
        provider_read_stop_time_ms=provider_read_stop_time_ms,
    )
    parquet_contract = _parquet_contract(
        Path(args.dataset),
        catalog=catalog,
        receipt=dataset_receipt,
        provider_read_stop_time_ms=provider_read_stop_time_ms,
    )
    model_contract = validate_model_contract(
        model,
        training_config=config["training"],
        expected_data_sha256=actual_data_sha,
        provider_read_start_time_ms=provider_read_start_time_ms,
        provider_read_stop_time_ms=provider_read_stop_time_ms,
    )
    actual_model_sha = hashlib.sha256(payloads["model"]).hexdigest()
    metrics_contract = validate_metrics_contract(
        metrics,
        model=model,
        expected_data_sha256=actual_data_sha,
        expected_model_file_sha256=actual_model_sha,
    )
    weekly_review = None
    if "weekly_review" in config:
        if "weekly_review" not in payloads:
            raise TrainingQualityError("V0.5 weekly review payload is required")
        weekly_review = json.loads(payloads.get("weekly_review") or b"{}")
        weekly_review_contract = validate_weekly_review_contract(
            weekly_review,
            expected_data_sha256=actual_data_sha,
            training_config=config["training"],
            review_config=config["weekly_review"],
        )

    generated_at = observed_at.isoformat().replace("+00:00", "Z")
    comparison_baseline: dict[str, object]
    if args.dry_run:
        baseline_dataset = bootstrap_baseline["dataset"]
        validate_catalog_quality(
            catalog,
            policy=policy,
            previous_market_count=int(baseline_dataset["market_count_requested"]),
        )
        dataset_quality = validate_dataset_receipt_quality(
            dataset_receipt,
            catalog=catalog,
            policy=policy,
            expected_catalog_sha256=actual_catalog_sha,
            expected_catalog_bytes=len(payloads["catalog"]),
            expected_dataset_sha256=actual_data_sha,
            expected_dataset_bytes=len(payloads["dataset"]),
            expected_last_open_time_ms=expected_last_open_time_ms,
            provider_read_stop_time_ms=provider_read_stop_time_ms,
            previous_receipt=bootstrap_baseline,
        )
        comparison_baseline = {
            "source": "FROZEN_V0_3_PASS_RECEIPT",
            "reference": config["data_quality"]["baseline_evidence"],
            "sha256": V0_3_BASELINE_EVIDENCE_SHA256,
            "market_count_requested": baseline_dataset["market_count_requested"],
            "market_count_audited": baseline_dataset["market_count_audited"],
            "row_count": baseline_dataset["row_count"],
            "bootstrap_used": True,
        }
        governance_evidence = {
            "config": governance_contract,
            "comparison_baseline": comparison_baseline,
        }
        objects = build_online_objects(
            config=config,
            run_id=args.run_id,
            dataset=payloads["dataset"],
            catalog=payloads["catalog"],
            dataset_receipt=payloads["dataset_receipt"],
            model=payloads["model"],
            metrics=payloads["metrics"],
            weekly_review=payloads.get("weekly_review"),
            governance_evidence=governance_evidence,
            generated_at_utc=generated_at,
        )
        result = {
            "status": "PREPARED",
            "stage": f"BINANCE_SPOT_R2_TRAINING_DRY_RUN_{schema_version.upper()}",
            "planned_write_bytes": sum(len(item.payload) for item in objects),
            "objects": [
                {
                    "role": item.role,
                    "key": item.key,
                    "bytes": len(item.payload),
                    "sha256": hashlib.sha256(item.payload).hexdigest(),
                    "immutable": item.immutable,
                }
                for item in objects
            ],
            "latest_pointer_written_last": objects[-1].role == "latest_pointer",
            "r2_client_constructed": False,
            "r2_writes_performed": False,
        }
    else:
        _require_online_write_window(config)
        store = R2Store(
            account_id=required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=required("R2_BUCKET_NAME"),
            access_key_id=required("R2_ACCESS_KEY_ID"),
            secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        )
        previous = _previous_dataset_receipt(
            store,
            config,
            governance_contract=governance_contract,
            before_access=lambda: _require_online_write_window(config),
        )
        if previous is None:
            comparison_receipt = bootstrap_baseline
            baseline_dataset = bootstrap_baseline["dataset"]
            comparison_baseline = {
                "source": "FROZEN_V0_3_PASS_RECEIPT",
                "reference": config["data_quality"]["baseline_evidence"],
                "sha256": V0_3_BASELINE_EVIDENCE_SHA256,
                "market_count_requested": baseline_dataset["market_count_requested"],
                "market_count_audited": baseline_dataset["market_count_audited"],
                "row_count": baseline_dataset["row_count"],
                "bootstrap_used": True,
            }
        else:
            comparison_receipt, comparison_baseline = previous
        previous_dataset = (
            comparison_receipt["dataset"]
            if comparison_receipt.get("schema")
            == "binance-spot-r2-automated-training-pass-v0.3"
            else comparison_receipt
        )
        validate_catalog_quality(
            catalog,
            policy=policy,
            previous_market_count=int(previous_dataset["market_count_requested"]),
        )
        dataset_quality = validate_dataset_receipt_quality(
            dataset_receipt,
            catalog=catalog,
            policy=config["data_quality"],
            expected_catalog_sha256=actual_catalog_sha,
            expected_catalog_bytes=len(payloads["catalog"]),
            expected_dataset_sha256=actual_data_sha,
            expected_dataset_bytes=len(payloads["dataset"]),
            expected_last_open_time_ms=expected_last_open_time_ms,
            provider_read_stop_time_ms=provider_read_stop_time_ms,
            previous_receipt=comparison_receipt,
        )
        governance_evidence = {
            "config": governance_contract,
            "comparison_baseline": comparison_baseline,
        }
        objects = build_online_objects(
            config=config,
            run_id=args.run_id,
            dataset=payloads["dataset"],
            catalog=payloads["catalog"],
            dataset_receipt=payloads["dataset_receipt"],
            model=payloads["model"],
            metrics=payloads["metrics"],
            weekly_review=payloads.get("weekly_review"),
            governance_evidence=governance_evidence,
            generated_at_utc=generated_at,
        )
        result = publish_online_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=int(config["storage"]["free_only_hard_stop_bytes"]),
            pass_stage=str(config["storage"]["publish_pass_stage"]),
            metadata_version=str(config["storage"]["schema_version"]),
            before_access=lambda: _require_online_write_window(config),
            before_write=lambda: _require_online_write_window(config),
        )
    result.update(
        {
            "generated_at_utc": generated_at,
            "run_id": args.run_id,
            "provider": "binance_spot",
            "execution_route": execution_route,
            "governance_contract": governance_contract,
            "comparison_baseline": comparison_baseline,
            "catalog_sha256": actual_catalog_sha,
            "dataset_sha256": actual_data_sha,
            "dataset_quality_gate": dataset_quality,
            "parquet_contract": parquet_contract,
            "model_contract": model_contract,
            "metrics_contract": metrics_contract,
            "weekly_review_contract": weekly_review_contract,
            "source_switch_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "stage": result["stage"], "objects": len(result.get("objects", []))}))
    return 0 if result["status"] in {"PASS", "PREPARED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
