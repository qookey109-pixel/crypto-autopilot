#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_autopilot.research.bitget_macd import (
    BitgetMacdResearchConfig,
    default_bitget_macd_candidate_grid,
    result_summary,
    run_bitget_macd_long_30m_research,
)
from crypto_autopilot.research.bitget_macd_real_history import (
    EXPECTED_DATASET_FINGERPRINT,
    select_governed_zec_15m_records,
    validate_contiguous_15m_history,
    validate_dataset_fingerprint,
)
from crypto_autopilot.research.bitget_macd_validation import (
    BitgetMacdValidationPlan,
    build_preregistered_windows,
    plan_sha256,
    run_preregistered_validation,
    validation_summary,
)
from crypto_autopilot.storage.parquet import parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training.history_quality import validate_training_partition


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-18-bitget-macd-zec-real-history-read-only-authority.json"
)
TRAINING_RUNNER = ROOT / "scripts/train_binance_detailed_history_models.py"
EXPECTED_PREREG_MAIN_SHA = "a0e216a41feaca61433bae9ca93c870a5baea9cc"


def _load_training_runner():
    spec = importlib.util.spec_from_file_location(
        "bitget_zec_readonly_training_index", TRAINING_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load governed Core100 dataset index helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


class _ReadOnlyStore:
    """Narrow R2 view intentionally exposing no write method."""

    __slots__ = ("_store",)

    def __init__(self, store: R2Store) -> None:
        self._store = store

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        return self._store.get_bytes_if_exists(key)

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        return self._store.get_bytes_verified(key, expected_sha256=expected_sha256)


def _create_read_only_store() -> _ReadOnlyStore:
    store = R2Store(
        account_id=_required("CLOUDFLARE_ACCOUNT_ID"),
        bucket=_required("R2_BUCKET_NAME"),
        access_key_id=_required("R2_ACCESS_KEY_ID"),
        secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
    )
    return _ReadOnlyStore(store)


def _load_execution_authority(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "qookey-bitget-macd-zec-real-history-read-only-authority-v0.1":
        raise RuntimeError("unsupported ZEC read-only authority schema")
    if receipt.get("status") != "AUTHORIZED_READ_ONLY_ONE_SHOT":
        raise RuntimeError("ZEC read-only authority is not active")
    if receipt.get("authorized_source_main_sha") != EXPECTED_PREREG_MAIN_SHA:
        raise RuntimeError("ZEC authority is not bound to the preregistered main")
    if receipt.get("expected_dataset_fingerprint") != EXPECTED_DATASET_FINGERPRINT:
        raise RuntimeError("ZEC authority dataset fingerprint mismatch")
    execution = receipt.get("execution") or {}
    if execution.get("one_shot") is not True or execution.get("max_runs") != 1:
        raise RuntimeError("ZEC authority must be one-shot")
    scope = receipt.get("authorized_scope") or {}
    required_scope = {
        "provider": "binance_usdm",
        "dataset": "crypto_core_100",
        "symbol": "ZECUSDT",
        "interval": "15m",
        "source_month_start": "2022-08",
        "source_month_end": "2026-07",
        "r2_catalog_reads_authorized": True,
        "r2_history_reads_authorized": True,
        "r2_writes_authorized": False,
        "provider_fallback_authorized": False,
    }
    for key, expected in required_scope.items():
        if scope.get(key) != expected:
            raise RuntimeError(f"ZEC authority scope mismatch: {key}")
    boundary = receipt.get("safety_boundary") or {}
    if not boundary or any(value is not False for value in boundary.values()):
        raise RuntimeError("ZEC safety boundary changed")
    return receipt


def _utc_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def _confirmation_source(candles, plan: BitgetMacdValidationPlan):
    _development, confirmation = build_preregistered_windows(candles, plan=plan)
    return tuple(
        candle
        for candle in candles
        if confirmation.start_time_ms <= candle.time_ms < confirmation.end_time_ms
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    authority = _load_execution_authority(args.authority)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("version") != "0.1.2" or config.get("provider") != "binance_usdm":
        raise RuntimeError("unexpected Core100 config")
    if config["scope"]["source_month_start"] != "2022-08":
        raise RuntimeError("Core100 source start changed")
    if config["scope"]["source_month_end"] != "2026-07":
        raise RuntimeError("Core100 source end changed")
    if config["authority"]["replacement_holdout_access_authorized"] is not False:
        raise RuntimeError("replacement holdout must remain closed")

    store = _create_read_only_store()
    training_runner = _load_training_runner()
    catalog, state, object_records, dataset_fingerprint = training_runner.load_dataset_index(
        store, config
    )
    validate_dataset_fingerprint(dataset_fingerprint)

    selection = select_governed_zec_15m_records(
        catalog=catalog,
        object_records=object_records,
    )

    candles = []
    quality_classes: Counter[str] = Counter()
    for record in selection.records:
        payload = store.get_bytes_verified(
            str(record["r2_key"]),
            expected_sha256=str(record["r2_sha256"]),
        )
        restored = parquet_to_candles(payload)
        quality_classes[validate_training_partition(record, restored)] += 1
        candles.extend(restored)

    candles = sorted(candles, key=lambda candle: candle.time_ms)
    validate_contiguous_15m_history(candles)
    expected_start_ms = _utc_ms("2022-08-01T00:00:00Z")
    expected_end_exclusive_ms = _utc_ms("2026-08-01T00:00:00Z")
    if candles[0].time_ms != expected_start_ms:
        raise RuntimeError("ZEC governed history does not begin at frozen source start")
    if candles[-1].time_ms != expected_end_exclusive_ms - 15 * 60 * 1000:
        raise RuntimeError("ZEC governed history does not end at frozen source end")
    if len(candles) != selection.source_rows:
        raise RuntimeError("ZEC combined row count does not match governed partitions")

    plan = BitgetMacdValidationPlan()
    configs = default_bitget_macd_candidate_grid()
    if len(configs) != 2304:
        raise RuntimeError("Bitget MACD candidate grid drifted from preregistration")

    baseline = BitgetMacdResearchConfig()
    baseline_full = run_bitget_macd_long_30m_research(
        candles_15m=candles,
        config=baseline,
        initial_equity_usd=10_000.0,
    )
    confirmation_candles = _confirmation_source(candles, plan)
    baseline_confirmation = []
    for slippage in plan.confirmation_slippage_stress_bps_per_side:
        stressed = replace(baseline, slippage_bps_per_side=slippage)
        baseline_confirmation.append(
            {
                "slippage_bps_per_side": slippage,
                "result": result_summary(
                    run_bitget_macd_long_30m_research(
                        candles_15m=confirmation_candles,
                        config=stressed,
                        initial_equity_usd=10_000.0,
                    )
                ),
            }
        )

    validation = run_preregistered_validation(
        candles_15m=candles,
        configs=configs,
        plan=plan,
        initial_equity_usd=10_000.0,
    )
    if validation.candidate_count != 2304:
        raise RuntimeError("preregistered candidate count mismatch")
    if len(validation.selected_development_candidates) != 24:
        raise RuntimeError("preregistered Top 24 selection mismatch")
    if validation.confirmation_used_for_selection:
        raise RuntimeError("confirmation leaked into parameter selection")
    if validation.formal_project_holdout_accessed:
        raise RuntimeError("formal project holdout was accessed")

    report = {
        "schema": "qookey-bitget-macd-zec-real-history-read-only-result-v0.1",
        "status": "PASS",
        "stage": "BITGET_MACD_ZEC_REAL_HISTORY_PREREGISTERED_VALIDATION_COMPLETE",
        "observed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": {
            "provider": "binance_usdm",
            "delivery": "governed_core100_r2",
            "dataset": "crypto_core_100",
            "dataset_fingerprint": dataset_fingerprint,
            "symbol": selection.symbol,
            "interval": selection.interval,
            "source_month_start": selection.start_period,
            "source_month_end": selection.end_period,
            "partition_count": selection.partition_count,
            "source_rows": selection.source_rows,
            "first_time_ms": candles[0].time_ms,
            "last_time_ms": candles[-1].time_ms,
            "record_fingerprint": selection.record_fingerprint,
            "quality_classes": dict(sorted(quality_classes.items())),
            "backfill_state_status": state.get("status"),
            "formal_replacement_holdout_accessed": False,
        },
        "preregistration": {
            "source_main_sha": EXPECTED_PREREG_MAIN_SHA,
            "plan_sha256": plan_sha256(plan),
            "candidate_grid_count": len(configs),
            "development_fraction": plan.development_fraction,
            "development_folds": plan.development_folds,
            "top_k": plan.top_k,
            "confirmation_slippage_stress_bps_per_side": list(
                plan.confirmation_slippage_stress_bps_per_side
            ),
            "confirmation_can_change_parameters": False,
        },
        "user_baseline": {
            "config": asdict(baseline),
            "full_period": result_summary(baseline_full),
            "confirmation_stress": baseline_confirmation,
        },
        "validation": validation_summary(validation),
        "execution": {
            "authority_schema": authority["schema"],
            "one_shot": True,
            "r2_catalog_reads_performed": True,
            "r2_history_reads_performed": True,
            "r2_writes_performed": False,
            "provider_requests_performed": 0,
            "raw_candles_persisted": False,
            "training_performed": False,
        },
        "authority": {
            "strategy_parameter_change_authorized": False,
            "formal_backtest_admission_authorized": False,
            "source_switch_authorized": False,
            "holdout_access_authorized": False,
            "model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "symbol": selection.symbol,
                "partitions": selection.partition_count,
                "rows": selection.source_rows,
                "candidate_count": validation.candidate_count,
                "selected": len(validation.selected_development_candidates),
                "dataset_fingerprint": dataset_fingerprint,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
