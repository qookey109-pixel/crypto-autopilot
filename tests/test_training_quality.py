from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq

import scripts.publish_binance_spot_training_to_r2 as publisher
from crypto_autopilot.lineage import sha256_json
from crypto_autopilot.training_quality import (
    TrainingQualityError,
    validate_catalog_quality,
    validate_dataset_receipt_quality,
    validate_weekly_review_contract,
)


FEATURE_NAMES = [
    "return_1d",
    "return_3d",
    "return_7d",
    "close_vs_ma7",
    "quote_volume_vs_ma7",
]
CATALOG_AUTHORITY = {
    "local_public_market_reads_authorized": True,
    "local_artifact_write_authorized": False,
    "github_actions_ephemeral_workspace_authorized": True,
    "website_projection_authorized": False,
    "production_r2_access_authorized": False,
    "provider_splicing_authorized": False,
    "pionex_native_relabel_authorized": False,
    "source_switch_authorized": False,
    "holdout_access_authorized": False,
    "trade_kline_w1_materialization_authorized": False,
    "formal_trade_plan_authorized": False,
    "real_money_order_authorized": False,
    "live_trading_authorized": False,
}
RESEARCH_AUTHORITY = {
    "source_switch_authorized": False,
    "holdout_accessed": False,
    "automatic_model_promotion_authorized": False,
    "automatic_trade_plan_authorized": False,
    "real_money_order_authorized": False,
    "live_trading_authorized": False,
}
V0_5_CONFIG = json.loads(
    Path("config/binance_spot_r2_training_governance_v0_5.json").read_text()
)
TEST_NOW = datetime(2026, 8, 23, tzinfo=UTC)
OPEN_TIME_MS = int(datetime(2026, 8, 22, tzinfo=UTC).timestamp() * 1000)
PROVIDER_STOP_TIME_MS = int(datetime(2026, 8, 27, tzinfo=UTC).timestamp() * 1000)


def json_payload(value: dict) -> bytes:
    return (json.dumps(value) + "\n").encode()


def catalog(count: int) -> dict:
    return {
        "schema": "binance-internal-training-market-catalog-v0.2",
        "status": "EPHEMERAL_BUILD_FOR_R2_AUTHORIZED",
        "provider": "binance_spot",
        "market_type": "spot",
        "source_endpoint": "https://data-api.binance.vision/api/v3/exchangeInfo",
        "quote_filter": {"all_quotes": False, "quotes": ["USDT", "USDC"]},
        "markets": [
            {
                "symbol": f"ASSET{index:04d}USDT",
                "base_asset": f"ASSET{index:04d}",
                "quote_asset": "USDT",
                "status": "TRADING",
                "market_type": "spot",
                "asset_class": "crypto",
                "classification_method": "test_fixture",
                "classification_confidence": "high",
                "is_spot_trading_allowed": True,
            }
            for index in range(count)
        ],
        "authority": dict(CATALOG_AUTHORITY),
    }


def receipt(
    current_catalog: dict,
    audited: int,
    *,
    catalog_bytes: bytes,
    dataset_bytes: bytes,
) -> dict:
    symbols = [str(item["symbol"]) for item in current_catalog["markets"]]
    requested = len(symbols)
    return {
        "schema": "binance-internal-training-run-v0.2",
        "status": "PASS",
        "provider": "binance_spot",
        "market_type": "spot",
        "interval": "1d",
        "generated_at_utc": "2026-08-23T00:00:00Z",
        "requested_start_utc": "2020-01-01T00:00:00Z",
        "captured_through_utc": "2026-08-22T00:00:00Z",
        "market_count_requested": requested,
        "market_count_with_rows": requested,
        "market_count_audited": audited,
        "row_count": requested,
        "asset_class_counts": {"crypto": requested},
        "quote_asset_counts": {"USDT": requested},
        "errors": {},
        "audit_failures": symbols[audited:],
        "market_audit_evidence": {
            symbol: {
                "audit_ok": index < audited,
                "expected_last_open_time_ms": OPEN_TIME_MS,
                "actual_first_open_time_ms": OPEN_TIME_MS,
                "actual_last_open_time_ms": OPEN_TIME_MS,
                "tail_missing_bars": 0,
                "tail_complete": True,
            }
            for index, symbol in enumerate(symbols)
        },
        "catalog": {
            "sha256": hashlib.sha256(catalog_bytes).hexdigest(),
            "bytes": len(catalog_bytes),
        },
        "parquet": {
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "bytes": len(dataset_bytes),
        },
        "authority": dict(CATALOG_AUTHORITY),
        "website_projection": {"authorized": False, "written": False},
    }


def policy() -> dict:
    return {
        "minimum_catalog_market_count": 500,
        "minimum_audited_market_fraction": 0.9,
        "maximum_provider_error_count": 0,
        "minimum_market_count_fraction_of_previous": 0.8,
        "minimum_audited_count_fraction_of_previous": 0.8,
        "minimum_row_count_fraction_of_previous": 0.8,
    }


def validate_receipt(
    current_catalog: dict,
    current_receipt: dict,
    *,
    catalog_bytes: bytes,
    dataset_bytes: bytes,
    previous_receipt: dict | None = None,
) -> dict:
    return validate_dataset_receipt_quality(
        current_receipt,
        catalog=current_catalog,
        policy=policy(),
        expected_catalog_sha256=hashlib.sha256(catalog_bytes).hexdigest(),
        expected_catalog_bytes=len(catalog_bytes),
        expected_dataset_sha256=hashlib.sha256(dataset_bytes).hexdigest(),
        expected_dataset_bytes=len(dataset_bytes),
        expected_last_open_time_ms=OPEN_TIME_MS,
        provider_read_stop_time_ms=PROVIDER_STOP_TIME_MS,
        previous_receipt=previous_receipt,
    )


def weekly_review(data_sha256: str) -> dict:
    candidate_metrics = {
        "samples": 10,
        "positive_rate": 0.5,
        "accuracy": 0.5,
        "log_loss": 0.693147,
        "brier_score": 0.25,
    }
    baseline_metrics = {
        **candidate_metrics,
        "train_positive_rate_probability": 0.5,
    }
    fold = {
        "status": "PASS",
        "train_end_exclusive_ms": OPEN_TIME_MS,
        "validation_end_exclusive_ms": OPEN_TIME_MS + 86_400_000,
        "train_samples": 20,
        "validation": candidate_metrics,
        "partition_integrity": {
            "status": "PASS",
            "failures": [],
            "train_record_count": 20,
            "validation_record_count": 10,
            "record_overlap_count": 0,
            "strictly_chronological": True,
            "train_records_sha256": "1" * 64,
            "validation_records_sha256": "2" * 64,
            "provider_source_overlap_expected": True,
            "holdout_status": "FROZEN_UNOPENED_NOT_ACCESSED",
            "holdout_accessed": False,
        },
        "baseline_comparison": {
            "status": "REJECT",
            "baseline": "train_prevalence_constant_probability",
            "required_positive_improvements": ["log_loss", "brier_score"],
            "candidate_metrics": candidate_metrics,
            "baseline_metrics": baseline_metrics,
            "improvements": {
                "accuracy": 0.0,
                "log_loss": 0.0,
                "brier_score": 0.0,
            },
            "brier_skill_score": 0.0,
        },
    }
    cost_scenarios = [
        {
            "name": configured["name"],
            "taker_fee_bps_each_side": float(configured["taker_fee_bps_each_side"]),
            "slippage_bps_each_fill": float(configured["slippage_bps_each_fill"]),
            "signal_count": 0,
            "active_days": 0,
            "mean_net_signal_return": 0.0,
            "diagnostic_final_equity_usd": 10000.0,
            "diagnostic_net_growth_pct": 0.0,
            "diagnostic_max_drawdown_pct": 0.0,
        }
        for configured in V0_5_CONFIG["weekly_review"]["cost_scenarios"]
    ]
    configured_base = next(
        item for item in cost_scenarios if item["name"] == "configured_base"
    )
    folds = []
    for index in range(3):
        value = deepcopy(fold)
        value["train_end_exclusive_ms"] = OPEN_TIME_MS + index * 86_400_000
        value["validation_end_exclusive_ms"] = OPEN_TIME_MS + (
            index + 1
        ) * 86_400_000
        value["partition_integrity"]["train_records_sha256"] = (
            f"{index + 1:x}" * 64
        )
        value["partition_integrity"]["validation_records_sha256"] = (
            f"{index + 4:x}" * 64
        )
        folds.append(value)
    return {
        "schema": "binance-spot-weekly-model-review-v0.5",
        "status": "PASS",
        "status_semantics": "PIPELINE_EVIDENCE_COMPLETED_NOT_MODEL_APPROVAL",
        "mode": "RESEARCH_DIAGNOSTICS_ONLY",
        "provider": "binance_spot",
        "data_sha256": data_sha256,
        "walk_forward": {
            "method": "expanding_train_non_overlapping_forward_validation",
            "classes": {
                "crypto": {
                    "status": "PASS",
                    "baseline_quality_status": "REJECT",
                    "example_count": 100,
                    "folds": folds,
                },
                "stablecoin": {
                    "status": "NOT_READY",
                    "baseline_quality_status": "NOT_READY",
                    "example_count": 0,
                    "folds": [],
                },
                "tokenized_stock_candidate": {
                    "status": "NOT_READY",
                    "baseline_quality_status": "NOT_READY",
                    "example_count": 0,
                    "folds": [],
                },
                "other": {
                    "status": "NOT_READY",
                    "baseline_quality_status": "NOT_READY",
                    "example_count": 0,
                    "folds": [],
                },
            },
        },
        "cost_and_drawdown_sensitivity": cost_scenarios,
        "asset_exposure": {
            "signal_count": 0,
            "maximum_concurrent_symbols": 0,
            "maximum_symbol_signal_share": 0.0,
            "symbol_signal_shares": {},
            "asset_class_signal_shares": {},
            "interpretation": (
                "Signal concentration proxy only; not an executed portfolio position ledger."
            ),
        },
        "model_quality_gate": {
            "status": "REJECT",
            "failures": [
                "READY_CLASSES_DID_NOT_BEAT_NAIVE_BASELINE_IN_EVERY_FOLD",
                "NO_OUT_OF_FOLD_LONG_SIGNALS",
                "NET_GROWTH_BELOW_POLICY",
            ],
            "baseline_rejected_asset_classes": ["crypto"],
            "integrity_failed_asset_classes": [],
            "policy": V0_5_CONFIG["weekly_review"]["quality_gate"],
            "evaluated_cost_scenario": configured_base,
            "promotion_eligible": False,
            "interpretation": (
                "Research evidence gate only. PASS does not authorize model promotion, "
                "backtest admission or trading."
            ),
        },
        "lineage": {
            "schema": "binance-spot-weekly-training-lineage-v0.5",
            "provider": "binance_spot",
            "dataset_sha256": data_sha256,
            "feature_contract_sha256": sha256_json(FEATURE_NAMES),
            "training_config_sha256": sha256_json(V0_5_CONFIG["training"]),
            "review_config_sha256": sha256_json(V0_5_CONFIG["weekly_review"]),
            "holdout_status": "FROZEN_UNOPENED_NOT_ACCESSED",
            "holdout_accessed": False,
            "source_switch_authorized": False,
        },
        "authority": {
            "formal_backtest_admission_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def model(data_sha256: str) -> dict:
    return {
        "schema": "binance-spot-daily-direction-model-v0.5",
        "status": "PASS",
        "mode": "RESEARCH_TRAINING_ONLY",
        "generated_at_utc": "2026-08-23T00:00:00Z",
        "provider": "binance_spot",
        "data_sha256": data_sha256,
        "target": "next_complete_daily_close_up",
        "feature_contract": {
            "schema": "binance-spot-daily-direction-features-v0.3",
            "ordered_names": list(FEATURE_NAMES),
        },
        "models": {
            "crypto": {
                "status": "PASS",
                "split_time_ms": OPEN_TIME_MS,
                "feature_names": list(FEATURE_NAMES),
                "feature_means": [0.0] * len(FEATURE_NAMES),
                "feature_standard_deviations": [1.0] * len(FEATURE_NAMES),
                "weights": [0.0] * len(FEATURE_NAMES),
                "bias": 0.0,
            },
            "stablecoin": {"status": "NOT_READY", "reason": "NO_EXAMPLES"},
            "tokenized_stock_candidate": {
                "status": "NOT_READY",
                "reason": "NO_EXAMPLES",
            },
            "other": {"status": "NOT_READY", "reason": "NO_EXAMPLES"},
        },
        "authority": dict(RESEARCH_AUTHORITY),
    }


def metrics(data_sha256: str, model_value: dict, model_bytes: bytes) -> dict:
    canonical = (
        json.dumps(model_value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    metric_block = {
        "samples": 10,
        "positive_rate": 0.5,
        "accuracy": 0.5,
        "log_loss": 0.693147,
        "brier_score": 0.25,
    }
    return {
        "schema": "binance-spot-daily-direction-training-metrics-v0.5",
        "status": "PASS",
        "mode": "RESEARCH_DIAGNOSTICS_ONLY",
        "generated_at_utc": model_value["generated_at_utc"],
        "provider": "binance_spot",
        "data_sha256": data_sha256,
        "model_canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "model_file_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "classes": {
            "crypto": {
                "status": "PASS",
                "examples": 20,
                "train": dict(metric_block),
                "test": dict(metric_block),
            },
            "stablecoin": {"status": "NOT_READY", "examples": 0},
            "tokenized_stock_candidate": {"status": "NOT_READY", "examples": 0},
            "other": {"status": "NOT_READY", "examples": 0},
        },
        "interpretation": (
            "Research diagnostics only; no strategy promotion or trading authority."
        ),
        "authority": dict(RESEARCH_AUTHORITY),
    }


def write_bundle(root: Path, *, count: int = 500, audited: int = 475) -> dict[str, Path]:
    catalog_value = catalog(count)
    catalog_bytes = json_payload(catalog_value)
    catalog_path = root / "catalog.json"
    catalog_path.write_bytes(catalog_bytes)

    rows = []
    for index, market in enumerate(catalog_value["markets"]):
        rows.append(
            {
                "provider": "binance_spot",
                "market_type": "spot",
                "asset_class": "crypto",
                "classification_method": "test_fixture",
                "classification_confidence": "high",
                "base_asset": market["base_asset"],
                "quote_asset": "USDT",
                "symbol": market["symbol"],
                "interval": "1d",
                "audit_ok": index < audited,
                "open_time_ms": OPEN_TIME_MS,
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "base_volume": 10.0,
                "quote_volume": 10.0,
                "trade_count": 1,
            }
        )
    dataset_path = root / "dataset.parquet"
    pq.write_table(pa.Table.from_pylist(rows), dataset_path)
    dataset_bytes = dataset_path.read_bytes()
    receipt_value = receipt(
        catalog_value,
        audited,
        catalog_bytes=catalog_bytes,
        dataset_bytes=dataset_bytes,
    )
    receipt_path = root / "dataset-receipt.json"
    receipt_path.write_bytes(json_payload(receipt_value))

    data_sha = hashlib.sha256(dataset_bytes).hexdigest()
    model_value = model(data_sha)
    model_bytes = json_payload(model_value)
    model_path = root / "model.json"
    model_path.write_bytes(model_bytes)
    metrics_path = root / "metrics.json"
    metrics_path.write_bytes(json_payload(metrics(data_sha, model_value, model_bytes)))
    review_path = root / "weekly-review.json"
    review_path.write_bytes(json_payload(weekly_review(data_sha)))
    return {
        "catalog": catalog_path,
        "dataset": dataset_path,
        "receipt": receipt_path,
        "model": model_path,
        "metrics": metrics_path,
        "review": review_path,
        "output": root / "publish-receipt.json",
    }


def publisher_argv(
    paths: dict[str, Path],
    *,
    dry_run: bool = False,
    event_name: str = "workflow_dispatch",
    activation_mode: str = "MANUAL_TRAINING",
) -> list[str]:
    values = [
        "publish_binance_spot_training_to_r2.py",
        "--config",
        "config/binance_spot_r2_training_governance_v0_5.json",
        "--catalog",
        str(paths["catalog"]),
        "--dataset",
        str(paths["dataset"]),
        "--dataset-receipt",
        str(paths["receipt"]),
        "--model",
        str(paths["model"]),
        "--metrics",
        str(paths["metrics"]),
        "--weekly-review",
        str(paths["review"]),
        "--event-name",
        event_name,
        "--activation-mode",
        activation_mode,
        "--output",
        str(paths["output"]),
    ]
    if dry_run:
        values.append("--dry-run")
    return values


class PreviousDatasetStore:
    def __init__(
        self, latest: dict, receipt_payload: bytes, catalog_payload: bytes = b"{}"
    ):
        self.latest_key = "training/binance_spot/daily-direction/v0.5/latest.json"
        self.objects = {
            self.latest_key: json_payload(latest),
            str(latest.get("catalog_key", "missing-catalog")): catalog_payload,
            str(latest["dataset_receipt_key"]): receipt_payload,
        }
        self.verified_reads: list[str] = []

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        self.verified_reads.append(key)
        payload = self.objects[key]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("fixture SHA mismatch")
        return payload


class TrainingQualityTests(unittest.TestCase):
    def test_online_write_window_closes_at_exact_stop(self) -> None:
        with (
            patch.object(
                publisher,
                "utc_now",
                return_value=datetime(2026, 8, 27, tzinfo=UTC),
            ),
            self.assertRaisesRegex(TrainingQualityError, "online write window is closed"),
        ):
            publisher._require_online_write_window(V0_5_CONFIG)

    def test_catalog_collapse_from_748_to_1_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            TrainingQualityError,
            "CATALOG_MARKET_COUNT_BELOW_ABSOLUTE_MINIMUM",
        ):
            validate_catalog_quality(catalog(1), policy=policy(), previous_market_count=748)

    def test_one_good_market_among_many_fails_audited_coverage(self) -> None:
        current_catalog = catalog(748)
        catalog_bytes = json_payload(current_catalog)
        dataset_bytes = b"dataset"
        with self.assertRaisesRegex(
            TrainingQualityError,
            "AUDITED_MARKET_FRACTION_BELOW_POLICY",
        ):
            validate_receipt(
                current_catalog,
                receipt(
                    current_catalog,
                    1,
                    catalog_bytes=catalog_bytes,
                    dataset_bytes=dataset_bytes,
                ),
                catalog_bytes=catalog_bytes,
                dataset_bytes=dataset_bytes,
            )

    def test_previous_dataset_collapse_fails_even_above_absolute_minimum(self) -> None:
        current_catalog = catalog(550)
        catalog_bytes = json_payload(current_catalog)
        dataset_bytes = b"current"
        previous_catalog = catalog(748)
        previous_receipt = receipt(
            previous_catalog,
            723,
            catalog_bytes=json_payload(previous_catalog),
            dataset_bytes=b"previous",
        )
        with self.assertRaisesRegex(
            TrainingQualityError,
            "DATASET_MARKET_COUNT_COLLAPSED_VS_PREVIOUS",
        ):
            validate_receipt(
                current_catalog,
                receipt(
                    current_catalog,
                    540,
                    catalog_bytes=catalog_bytes,
                    dataset_bytes=dataset_bytes,
                ),
                catalog_bytes=catalog_bytes,
                dataset_bytes=dataset_bytes,
                previous_receipt=previous_receipt,
            )

    def test_head_truncated_dataset_row_count_fails_closed(self) -> None:
        current_catalog = catalog(500)
        catalog_bytes = json_payload(current_catalog)
        dataset_bytes = b"current"
        previous_receipt = receipt(
            current_catalog,
            475,
            catalog_bytes=catalog_bytes,
            dataset_bytes=b"previous",
        )
        previous_receipt["row_count"] = 1000
        with self.assertRaisesRegex(
            TrainingQualityError,
            "DATASET_ROW_COUNT_COLLAPSED_VS_PREVIOUS",
        ):
            validate_receipt(
                current_catalog,
                receipt(
                    current_catalog,
                    475,
                    catalog_bytes=catalog_bytes,
                    dataset_bytes=dataset_bytes,
                ),
                catalog_bytes=catalog_bytes,
                dataset_bytes=dataset_bytes,
                previous_receipt=previous_receipt,
            )

    def test_valid_coverage_and_rejected_model_are_preserved_as_evidence(self) -> None:
        current_catalog = catalog(600)
        catalog_bytes = json_payload(current_catalog)
        dataset_bytes = b"dataset"
        evidence = validate_receipt(
            current_catalog,
            receipt(
                current_catalog,
                580,
                catalog_bytes=catalog_bytes,
                dataset_bytes=dataset_bytes,
            ),
            catalog_bytes=catalog_bytes,
            dataset_bytes=dataset_bytes,
        )
        self.assertEqual(evidence["status"], "PASS")
        data_sha = "a" * 64
        contract = validate_weekly_review_contract(
            weekly_review(data_sha),
            expected_data_sha256=data_sha,
            training_config=V0_5_CONFIG["training"],
            review_config=V0_5_CONFIG["weekly_review"],
        )
        self.assertEqual(contract["model_quality_status"], "REJECT")
        self.assertFalse(contract["promotion_eligible"])

    def test_stale_or_post_stop_dataset_coverage_fails_closed(self) -> None:
        current_catalog = catalog(500)
        catalog_bytes = json_payload(current_catalog)
        dataset_bytes = b"dataset"
        for label, timestamp_ms, captured in (
            (
                "stale",
                OPEN_TIME_MS - 86_400_000,
                "2026-08-21T00:00:00Z",
            ),
            (
                "post_stop",
                int(datetime(2026, 8, 28, tzinfo=UTC).timestamp() * 1000),
                "2026-08-28T00:00:00Z",
            ),
        ):
            with self.subTest(case=label):
                value = receipt(
                    current_catalog,
                    500,
                    catalog_bytes=catalog_bytes,
                    dataset_bytes=dataset_bytes,
                )
                value["captured_through_utc"] = captured
                for evidence in value["market_audit_evidence"].values():
                    evidence["expected_last_open_time_ms"] = timestamp_ms
                    evidence["actual_first_open_time_ms"] = timestamp_ms
                    evidence["actual_last_open_time_ms"] = timestamp_ms
                with self.assertRaisesRegex(
                    TrainingQualityError,
                    "dataset receipt UTC coverage is not daily aligned",
                ):
                    validate_receipt(
                        current_catalog,
                        value,
                        catalog_bytes=catalog_bytes,
                        dataset_bytes=dataset_bytes,
                    )

    def test_parquet_gap_rejected_only_for_audited_series(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_bundle(root, count=10, audited=9)
            catalog_value = json.loads(paths["catalog"].read_text())
            receipt_value = json.loads(paths["receipt"].read_text())
            rows = pq.read_table(paths["dataset"]).to_pylist()
            failed_symbol = catalog_value["markets"][-1]["symbol"]
            extra = dict(next(item for item in rows if item["symbol"] == failed_symbol))
            extra["open_time_ms"] = OPEN_TIME_MS - 2 * 86_400_000
            rows.append(extra)
            pq.write_table(pa.Table.from_pylist(rows), paths["dataset"])
            receipt_value["row_count"] += 1
            receipt_value["market_audit_evidence"][failed_symbol][
                "actual_first_open_time_ms"
            ] = extra["open_time_ms"]
            contract = publisher._parquet_contract(
                paths["dataset"],
                catalog=catalog_value,
                receipt=receipt_value,
                provider_read_stop_time_ms=PROVIDER_STOP_TIME_MS,
            )
            self.assertEqual(contract["status"], "PASS")

            audited_symbol = catalog_value["markets"][0]["symbol"]
            extra = dict(next(item for item in rows if item["symbol"] == audited_symbol))
            extra["open_time_ms"] = OPEN_TIME_MS - 2 * 86_400_000
            rows.append(extra)
            pq.write_table(pa.Table.from_pylist(rows), paths["dataset"])
            receipt_value["row_count"] += 1
            receipt_value["market_audit_evidence"][audited_symbol][
                "actual_first_open_time_ms"
            ] = extra["open_time_ms"]
            with self.assertRaisesRegex(
                TrainingQualityError,
                "Parquet daily coverage contains gaps or duplicates",
            ):
                publisher._parquet_contract(
                    paths["dataset"],
                    catalog=catalog_value,
                    receipt=receipt_value,
                    provider_read_stop_time_ms=PROVIDER_STOP_TIME_MS,
                )

    def test_parquet_ohlcv_corruption_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory), count=2, audited=2)
            catalog_value = json.loads(paths["catalog"].read_text())
            receipt_value = json.loads(paths["receipt"].read_text())
            rows = pq.read_table(paths["dataset"]).to_pylist()
            rows[0]["high"] = 0.5
            pq.write_table(pa.Table.from_pylist(rows), paths["dataset"])
            with self.assertRaisesRegex(
                TrainingQualityError,
                "Parquet OHLCV values violate market-data bounds",
            ):
                publisher._parquet_contract(
                    paths["dataset"],
                    catalog=catalog_value,
                    receipt=receipt_value,
                    provider_read_stop_time_ms=PROVIDER_STOP_TIME_MS,
                )

    def test_weekly_quality_gate_is_recomputed_from_evidence(self) -> None:
        data_sha = "a" * 64
        false_green = weekly_review(data_sha)
        false_green["model_quality_gate"]["status"] = "PASS"
        false_green["model_quality_gate"]["failures"] = []
        with self.assertRaisesRegex(
            TrainingQualityError, "model-quality semantics mismatch"
        ):
            validate_weekly_review_contract(
                false_green,
                expected_data_sha256=data_sha,
                training_config=V0_5_CONFIG["training"],
                review_config=V0_5_CONFIG["weekly_review"],
            )

        false_improvement = weekly_review(data_sha)
        false_improvement["walk_forward"]["classes"]["crypto"]["folds"][0][
            "baseline_comparison"
        ]["improvements"]["log_loss"] = 0.5
        with self.assertRaisesRegex(
            TrainingQualityError, "improvement arithmetic mismatch"
        ):
            validate_weekly_review_contract(
                false_improvement,
                expected_data_sha256=data_sha,
                training_config=V0_5_CONFIG["training"],
                review_config=V0_5_CONFIG["weekly_review"],
            )

        hidden_integrity_failure = weekly_review(data_sha)
        failed_fold = {
            "status": "INTEGRITY_FAIL",
            "train_samples": 5,
            "validation_samples": 5,
            "partition_integrity": {
                "status": "FAIL",
                "failures": ["TRAIN_VALIDATION_RECORD_OVERLAP"],
                "train_record_count": 5,
                "validation_record_count": 5,
            },
        }
        hidden_integrity_failure["walk_forward"]["classes"]["stablecoin"] = {
            "status": "FAIL",
            "baseline_quality_status": "NOT_READY",
            "example_count": 10,
            "folds": [deepcopy(failed_fold) for _ in range(3)],
        }
        with self.assertRaisesRegex(
            TrainingQualityError, "model-quality semantics mismatch"
        ):
            validate_weekly_review_contract(
                hidden_integrity_failure,
                expected_data_sha256=data_sha,
                training_config=V0_5_CONFIG["training"],
                review_config=V0_5_CONFIG["weekly_review"],
            )

    def test_weekly_fold_cost_and_exposure_identities_fail_closed(self) -> None:
        data_sha = "a" * 64
        duplicate_fold = weekly_review(data_sha)
        duplicate_fold["walk_forward"]["classes"]["crypto"]["folds"][1] = deepcopy(
            duplicate_fold["walk_forward"]["classes"]["crypto"]["folds"][0]
        )
        sample_mismatch = weekly_review(data_sha)
        sample_mismatch["walk_forward"]["classes"]["crypto"]["folds"][0][
            "train_samples"
        ] += 1
        growth_mismatch = weekly_review(data_sha)
        growth_mismatch["cost_and_drawdown_sensitivity"][0][
            "diagnostic_net_growth_pct"
        ] = 1.0
        exposure_mismatch = weekly_review(data_sha)
        for scenario in exposure_mismatch["cost_and_drawdown_sensitivity"]:
            scenario["signal_count"] = 1
        exposure_mismatch["asset_exposure"] = {
            "signal_count": 1,
            "maximum_concurrent_symbols": 1,
            "maximum_symbol_signal_share": 0.9,
            "symbol_signal_shares": {"BTCUSDT": 0.8, "ETHUSDT": 0.2},
            "asset_class_signal_shares": {"crypto": 1.0},
            "interpretation": (
                "Signal concentration proxy only; not an executed portfolio position ledger."
            ),
        }
        for value, message in (
            (duplicate_fold, "fold windows overlap or do not advance"),
            (sample_mismatch, "fold sample lineage mismatch"),
            (growth_mismatch, "final equity and net growth do not reconcile"),
            (exposure_mismatch, "exposure shares are inconsistent"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                TrainingQualityError, message
            ):
                validate_weekly_review_contract(
                    value,
                    expected_data_sha256=data_sha,
                    training_config=V0_5_CONFIG["training"],
                    review_config=V0_5_CONFIG["weekly_review"],
                )

    def test_previous_dataset_pointer_is_namespace_allowlisted(self) -> None:
        previous_catalog = catalog(600)
        previous_catalog_payload = json_payload(previous_catalog)
        previous_dataset_payload = b"previous"
        previous = receipt(
            previous_catalog,
            580,
            catalog_bytes=previous_catalog_payload,
            dataset_bytes=previous_dataset_payload,
        )
        payload = json_payload(previous)
        run_id = "github-1-1"
        key = (
            "market-data/binance_spot/internal-training/v0.5/"
            f"runs/run={run_id}/dataset-receipt.json"
        )
        latest = {
            "schema": "binance-spot-r2-automated-training-latest-v0.5",
            "provider": "binance_spot",
            "run_id": run_id,
            "catalog_key": (
                "market-data/binance_spot/internal-training/v0.5/"
                f"runs/run={run_id}/market-catalog.json"
            ),
            "catalog_sha256": hashlib.sha256(previous_catalog_payload).hexdigest(),
            "dataset_key": (
                "market-data/binance_spot/internal-training/v0.5/"
                f"runs/run={run_id}/binance-spot-1d.parquet"
            ),
            "dataset_sha256": hashlib.sha256(previous_dataset_payload).hexdigest(),
            "dataset_receipt_key": key,
            "dataset_receipt_sha256": hashlib.sha256(payload).hexdigest(),
        }
        config = json.loads(
            Path("config/binance_spot_r2_training_governance_v0_5.json").read_text()
        )
        config_path = Path(
            "config/binance_spot_r2_training_governance_v0_5.json"
        )
        _, governance_contract = publisher.load_v0_5_authority_pair(
            config,
            config_path=config_path,
            config_payload=config_path.read_bytes(),
            repository_root=Path.cwd(),
        )
        previous_governance = {
            "config": governance_contract,
            "comparison_baseline": {
                "source": "FROZEN_V0_3_PASS_RECEIPT",
                "sha256": "3" * 64,
            },
        }
        latest["governance"] = previous_governance
        latest["governance_sha256"] = hashlib.sha256(
            publisher.json_bytes(previous_governance)
        ).hexdigest()
        store = PreviousDatasetStore(latest, payload, previous_catalog_payload)
        loaded = publisher._previous_dataset_receipt(
            store,
            config,
            governance_contract=governance_contract,
        )
        assert loaded is not None
        self.assertEqual(loaded[0]["market_count_audited"], 580)
        self.assertEqual(loaded[1]["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(store.verified_reads, [latest["catalog_key"], key])

        for invalid_key in (
            "holdout/binance_spot/replacement/dataset-receipt.json",
            "market-data/binance_spot/internal-training/v0.5/raw/provider.json",
        ):
            with self.subTest(key=invalid_key):
                invalid_latest = {**latest, "dataset_receipt_key": invalid_key}
                invalid_store = PreviousDatasetStore(
                    invalid_latest, payload, previous_catalog_payload
                )
                with self.assertRaisesRegex(TrainingQualityError, "outside its namespace"):
                    publisher._previous_dataset_receipt(
                        invalid_store,
                        config,
                        governance_contract=governance_contract,
                    )
                self.assertEqual(invalid_store.verified_reads, [])

    def test_unsafe_weekly_review_stops_at_review_gate_before_r2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory))
            unsafe_review = json.loads(paths["review"].read_text())
            unsafe_review["lineage"]["holdout_accessed"] = True
            paths["review"].write_bytes(json_payload(unsafe_review))
            with (
                patch.object(sys, "argv", publisher_argv(paths)),
                patch.object(publisher, "utc_now", return_value=TEST_NOW),
                patch.object(publisher, "R2Store") as r2_store,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "weekly review lineage crossed a safety boundary",
                ),
            ):
                publisher.main()
            r2_store.assert_not_called()

    def test_model_provider_and_authority_stop_before_r2(self) -> None:
        for field, value, message in (
            ("provider", "pionex", "model identity or lineage mismatch"),
            ("live_trading_authorized", True, "unsafe V0.5 model authority"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                paths = write_bundle(Path(directory))
                model_value = json.loads(paths["model"].read_text())
                if field == "provider":
                    model_value[field] = value
                else:
                    model_value["authority"][field] = value
                paths["model"].write_bytes(json_payload(model_value))
                with (
                    patch.object(sys, "argv", publisher_argv(paths)),
                    patch.object(publisher, "utc_now", return_value=TEST_NOW),
                    patch.object(publisher, "R2Store") as r2_store,
                    self.assertRaisesRegex(TrainingQualityError, message),
                ):
                    publisher.main()
                r2_store.assert_not_called()

    def test_model_split_before_dataset_start_stops_before_r2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory))
            model_value = json.loads(paths["model"].read_text())
            model_value["models"]["crypto"]["split_time_ms"] = 0
            paths["model"].write_bytes(json_payload(model_value))
            with (
                patch.object(sys, "argv", publisher_argv(paths)),
                patch.object(publisher, "utc_now", return_value=TEST_NOW),
                patch.object(publisher, "R2Store") as r2_store,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "model split timestamp is invalid",
                ),
            ):
                publisher.main()
            r2_store.assert_not_called()

    def test_dataset_receipt_sha_mismatch_stops_before_r2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory))
            receipt_value = json.loads(paths["receipt"].read_text())
            receipt_value["parquet"]["sha256"] = "0" * 64
            paths["receipt"].write_bytes(json_payload(receipt_value))
            with (
                patch.object(sys, "argv", publisher_argv(paths)),
                patch.object(publisher, "utc_now", return_value=TEST_NOW),
                patch.object(publisher, "R2Store") as r2_store,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "dataset receipt Parquet binding mismatch",
                ),
            ):
                publisher.main()
            r2_store.assert_not_called()

    def test_empty_metrics_shell_stops_before_r2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory))
            metrics_value = json.loads(paths["metrics"].read_text())
            del metrics_value["classes"]["crypto"]["train"]
            paths["metrics"].write_bytes(json_payload(metrics_value))
            with (
                patch.object(sys, "argv", publisher_argv(paths)),
                patch.object(publisher, "utc_now", return_value=TEST_NOW),
                patch.object(publisher, "R2Store") as r2_store,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "metrics.crypto.train must be an object",
                ),
            ):
                publisher.main()
            r2_store.assert_not_called()

    def test_overlapping_metrics_partition_counts_stop_before_r2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory))
            metrics_value = json.loads(paths["metrics"].read_text())
            metrics_value["classes"]["crypto"]["examples"] = 10
            paths["metrics"].write_bytes(json_payload(metrics_value))
            with (
                patch.object(sys, "argv", publisher_argv(paths)),
                patch.object(publisher, "utc_now", return_value=TEST_NOW),
                patch.object(publisher, "R2Store") as r2_store,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "metrics sample counts are inconsistent",
                ),
            ):
                publisher.main()
            r2_store.assert_not_called()

    def test_first_v05_run_uses_frozen_748_market_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = write_bundle(Path(directory), count=550, audited=540)
            store = MagicMock()
            store.get_bytes_if_exists.return_value = None
            with (
                patch.object(sys, "argv", publisher_argv(paths)),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(publisher, "R2Store", return_value=store) as r2_store,
                patch.object(
                    publisher,
                    "utc_now",
                    return_value=TEST_NOW,
                ),
                patch.object(publisher, "publish_online_objects") as publish,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "CATALOG_MARKET_COUNT_COLLAPSED_VS_PREVIOUS",
                ),
            ):
                publisher.main()
            r2_store.assert_called_once()
            publish.assert_not_called()

if __name__ == "__main__":
    unittest.main()
