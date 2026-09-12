#!/usr/bin/env python3
"""Training entry point with exact history-quality revalidation before feature use."""
from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any

from crypto_autopilot.training.history_quality import (
    TrainingHistoryQualityError,
    validate_training_partition,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/train_binance_detailed_history_models.py"
spec = importlib.util.spec_from_file_location("binance_detailed_training_runner_v0_2", RUNNER)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def build_examples_from_r2(
    store,
    *,
    catalog: dict[str, Any],
    object_records: list[dict[str, Any]],
    config: dict[str, Any],
):
    """Use the original feature builder after each R2 partition is revalidated."""
    catalog_by_symbol = {str(item["symbol"]): item for item in catalog["markets"]}
    records_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in object_records:
        symbol = str(record.get("symbol") or "")
        if record.get("provider") != "binance_usdm" or symbol not in catalog_by_symbol:
            raise runner.DetailedHistoryAuthorityError(
                "detailed-history training object contract mismatch"
            )
        records_by_symbol[symbol].append(record)

    training = config["training"]
    base_cost = next(item for item in training["cost_scenarios"] if item["name"] == "base")
    label_cost = 2.0 * (
        float(base_cost["fee_bps_per_side"]) + float(base_cost["slippage_bps_per_side"])
    )
    all_examples = []
    for symbol in sorted(records_by_symbol):
        records = records_by_symbol[symbol]
        by_interval_period = {
            (str(item["interval"]), str(item["period"])): item for item in records
        }
        periods_by_interval = {
            interval: {
                period
                for observed_interval, period in by_interval_period
                if observed_interval == interval
            }
            for interval in ("15m", "1h", "4h")
        }
        common_periods = sorted(set.intersection(*periods_by_interval.values()))
        symbol_examples = []
        for segment in runner._contiguous_period_segments(common_periods):
            candles_by_interval = {}
            for interval in ("15m", "1h", "4h"):
                candles = []
                for period in segment:
                    record = by_interval_period[(interval, period)]
                    payload = store.get_bytes_verified(
                        record["r2_key"], expected_sha256=record["r2_sha256"]
                    )
                    restored = runner.parquet_to_candles(payload)
                    try:
                        validate_training_partition(record, restored)
                    except TrainingHistoryQualityError as exc:
                        raise runner.DetailedHistoryAuthorityError(
                            "detailed-history training partition quality mismatch"
                        ) from exc
                    candles.extend(restored)
                candles_by_interval[interval] = tuple(candles)
            symbol_examples.extend(
                runner.build_intraday_examples(
                    symbol=symbol,
                    asset_class=str(catalog_by_symbol[symbol]["asset_class"]),
                    candles_by_interval=candles_by_interval,
                    sample_stride_15m_bars=int(training["sample_stride_15m_bars"]),
                    forward_horizon_15m_bars=int(training["forward_horizon_15m_bars"]),
                    label_cost_bps_round_trip=label_cost,
                )
            )
        all_examples.extend(
            runner.bound_examples(
                symbol_examples, int(training["maximum_examples_per_symbol"])
            )
        )
    return runner.bound_examples(all_examples, int(training["maximum_total_examples"]))


runner.build_examples_from_r2 = build_examples_from_r2


def main() -> int:
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
