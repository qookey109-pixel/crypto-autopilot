from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence

from crypto_autopilot.backtest import BacktestConfig, LongTradePlan, run_long_backtest
from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.risk import RiskConfig
from crypto_autopilot.technical import build_technical_series, latest_closed_snapshot

SYMBOL = "BTC_USDT_PERP"
INTERVALS = ("15M", "60M", "4H")
START_MS = 1_785_542_400_000
END_MS = 1_787_875_200_000
COVERAGE = "COMPLETE_FIXED_27_DAY_CAPACITY_SAMPLE_ONLY"
RECEIPT_SCHEMA = "pionex-capacity-pilot-v0.2"
V0_2_CONFIG_SHA256 = "a66fdf7def02023590163091fbdd1eceabe5d96a774ffa0207e7b7a7f506f932"
V0_2_NAMESPACE = "market-data/pionex/historical-research-pool-v0.2/pilot"


class SimulationReadinessError(RuntimeError):
    pass


def _validate_receipt(receipt: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    expected = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "provider": "pionex_public_futures",
        "symbol": SYMBOL,
        "config_sha256": V0_2_CONFIG_SHA256,
        "coverage_claim": COVERAGE,
        "start_utc": "2026-08-01T00:00:00Z",
        "end_exclusive_utc": "2026-08-28T00:00:00Z",
        "holdout_accessed": False,
        "live_trading_authorized": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise SimulationReadinessError(f"V0.2 receipt mismatch: {key}")

    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or re.fullmatch(r"github-[0-9]+-1", run_id) is None:
        raise SimulationReadinessError("V0.2 receipt run_id is invalid")
    raw = receipt.get("intervals")
    if not isinstance(raw, list):
        raise SimulationReadinessError("V0.2 receipt intervals are required")

    details: dict[str, Mapping[str, object]] = {}
    for item in raw:
        if not isinstance(item, Mapping) or not isinstance(item.get("interval"), str):
            raise SimulationReadinessError("invalid V0.2 interval receipt")
        interval = item["interval"]
        if interval in details:
            raise SimulationReadinessError("duplicate V0.2 interval receipt")
        details[interval] = item
    if set(details) != set(INTERVALS):
        raise SimulationReadinessError("exact V0.2 receipt intervals are required")

    for interval in INTERVALS:
        step = INTERVAL_MS[interval]
        item = details[interval]
        digest = item.get("sha256")
        size = item.get("bytes")
        key = f"{V0_2_NAMESPACE}/run={run_id}/{interval}.parquet"
        if (
            item.get("rows") != (END_MS - START_MS) // step
            or item.get("first_time_ms") != START_MS
            or item.get("last_time_ms") != END_MS - step
            or item.get("key") != key
            or not isinstance(size, int)
            or size <= 0
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise SimulationReadinessError(f"V0.2 receipt coverage mismatch: {interval}")
    return details


def _validate_candles(
    candles_by_interval: Mapping[str, Sequence[Candle]],
) -> dict[str, tuple[Candle, ...]]:
    if set(candles_by_interval) != set(INTERVALS):
        raise SimulationReadinessError("exact 15M/60M/4H dataset is required")
    result: dict[str, tuple[Candle, ...]] = {}
    for interval in INTERVALS:
        candles = tuple(candles_by_interval[interval])
        step = INTERVAL_MS[interval]
        if not audit_candles(candles, interval).ok:
            raise SimulationReadinessError(f"candle audit failed: {interval}")
        if (
            len(candles) != (END_MS - START_MS) // step
            or not candles
            or candles[0].time_ms != START_MS
            or candles[-1].time_ms != END_MS - step
        ):
            raise SimulationReadinessError(f"fixed coverage mismatch: {interval}")
        result[interval] = candles
    return result


def load_verified_sample(
    parquet_by_interval: Mapping[str, bytes],
    receipt: Mapping[str, object],
) -> dict[str, tuple[Candle, ...]]:
    if set(parquet_by_interval) != set(INTERVALS):
        raise SimulationReadinessError("exact three V0.2 Parquet payloads are required")
    details = _validate_receipt(receipt)
    from crypto_autopilot.storage.parquet import parquet_to_candles

    decoded: dict[str, tuple[Candle, ...]] = {}
    for interval in INTERVALS:
        payload = parquet_by_interval[interval]
        if len(payload) != details[interval]["bytes"]:
            raise SimulationReadinessError(f"Parquet byte size mismatch: {interval}")
        if hashlib.sha256(payload).hexdigest() != details[interval]["sha256"]:
            raise SimulationReadinessError(f"Parquet SHA-256 mismatch: {interval}")
        decoded[interval] = tuple(parquet_to_candles(payload))
    return _validate_candles(decoded)


def _trend(snapshot, *, max_extension: float | None) -> bool:
    if not snapshot.ready:
        return False
    values = (snapshot.ema20, snapshot.ema50, snapshot.ema20_slope)
    if any(value is None or not math.isfinite(value) for value in values):
        return False
    if not (
        snapshot.ema20 > snapshot.ema50
        and snapshot.ema20_slope > 0
        and snapshot.close > snapshot.ema20
    ):
        return False
    if max_extension is None:
        return True
    value = snapshot.extension_from_ema20_atr
    return value is not None and math.isfinite(value) and value <= max_extension


def generate_plans(
    candles_by_interval: Mapping[str, Sequence[Candle]],
) -> tuple[LongTradePlan, ...]:
    """Generate simulation-only LONG plans without invented SState probabilities."""
    candles = _validate_candles(candles_by_interval)
    series = {
        interval: build_technical_series(candles[interval], interval)
        for interval in INTERVALS
    }
    entry_candles = {candle.time_ms: candle for candle in candles["15M"]}
    plans: list[LongTradePlan] = []
    for entry in series["15M"]:
        if not entry.ready:
            continue
        hour = latest_closed_snapshot(series["60M"], entry.available_at_ms, require_ready=True)
        four_hour = latest_closed_snapshot(series["4H"], entry.available_at_ms, require_ready=True)
        if hour is None or four_hour is None or not _trend(four_hour, max_extension=None):
            continue
        if not _trend(hour, max_extension=2.5):
            continue

        candle = entry_candles[entry.bar_time_ms]
        assert entry.ema20 is not None and entry.atr14 is not None
        assert entry.previous_high is not None and entry.volume_ratio is not None
        if not (
            candle.low <= entry.ema20 + 0.25 * entry.atr14
            and candle.close > entry.ema20
            and candle.close > entry.previous_high
            and entry.volume_ratio >= 1.0
        ):
            continue
        stop = min(candle.low, entry.ema20) - 0.25 * entry.atr14
        if stop <= 0 or stop >= candle.close:
            continue
        target = candle.close + 2.0 * (candle.close - stop)
        plans.append(
            LongTradePlan(
                f"simulation-v0.3-{entry.bar_time_ms}",
                SYMBOL,
                entry.bar_time_ms,
                stop,
                target,
            )
        )
    return tuple(plans)


def run_readiness(
    parquet_by_interval: Mapping[str, bytes],
    receipt: Mapping[str, object],
) -> dict[str, object]:
    candles = load_verified_sample(parquet_by_interval, receipt)
    plans = generate_plans(candles)
    if not plans:
        return {
            "status": "PIPELINE_NOT_EXERCISED_NO_SIGNAL",
            "data_ready": True,
            "pipeline_exercised": False,
            "full_simulation_ready": False,
            "generated_plan_count": 0,
            "executed_trade_count": 0,
            "blockers": ["no_candle_derived_strategy_signal", "historical_funding_evidence_missing"],
        }

    result = run_long_backtest(
        candles_by_symbol={SYMBOL: candles["15M"]},
        plans=plans,
        config=BacktestConfig(
            initial_equity_usd=100.0,
            taker_fee_bps=5.0,
            slippage_bps=2.0,
            risk=RiskConfig(
                risk_fraction_per_trade=0.01,
                max_leverage=3.0,
                daily_loss_limit_r=3.0,
                max_new_trades_per_day=3,
            ),
            max_holding_minutes=720,
        ),
    )
    exercised = bool(result.trades)
    return {
        "status": "PIPELINE_PASS_KLINE_ONLY" if exercised else "PIPELINE_NOT_EXERCISED",
        "data_ready": True,
        "pipeline_exercised": exercised,
        "full_simulation_ready": False,
        "generated_plan_count": len(plans),
        "executed_trade_count": len(result.trades),
        "rejected_plan_count": len(result.rejected_plans),
        "blockers": ["historical_funding_evidence_missing"],
        "result": result,
    }
