from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

from crypto_autopilot.backtest import BacktestConfig, FundingPoint, run_long_backtest
from crypto_autopilot.paper.simulation_readiness_v0_3 import (
    SYMBOL,
    generate_plans,
    load_verified_sample,
)
from crypto_autopilot.risk import RiskConfig

FUNDING_REPORT_SCHEMA = "pionex-funding-history-run-report-v0.1"
FUNDING_PROTOCOL_SHA256 = "9117e707203b35ef9d7420b96033cd339b97c549f03e3cdae2ecece4637b6834"
FUNDING_EXECUTION_SHA256 = "d2cdafc5900573eb7d9971b7e3d7b9e5e34f50d16a510b56dcd7e0512b5e3315"
START_MS = 1_785_542_400_000
END_MS = 1_787_875_200_000


class SimulationFundingError(RuntimeError):
    pass


def load_verified_funding(
    report: Mapping[str, object],
) -> tuple[FundingPoint, ...]:
    """Validate one exact funding PASS report and convert it to canonical points."""

    expected = {
        "schema": FUNDING_REPORT_SCHEMA,
        "status": "PASS",
        "protocol_config_sha256": FUNDING_PROTOCOL_SHA256,
        "execution_config_sha256": FUNDING_EXECUTION_SHA256,
        "event": "workflow_dispatch",
        "head_ref": "refs/heads/main",
        "repository": "qookey109-pixel/crypto-autopilot",
        "api_key_used": False,
        "private_api_used": False,
        "raw_provider_payloads_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "simulation_data_admission_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
        "provider": "pionex_public_futures",
        "symbol": SYMBOL,
        "window_start_utc": "2026-08-01T00:00:00Z",
        "window_end_exclusive_utc": "2026-08-28T00:00:00Z",
        "left_boundary_reached": True,
        "automatic_retries": 0,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise SimulationFundingError(f"funding report mismatch: {key}")

    run_id = report.get("run_id")
    run_attempt = report.get("run_attempt")
    if not isinstance(run_id, str) or re.fullmatch(r"[0-9]+", run_id) is None:
        raise SimulationFundingError("funding run_id is invalid")
    if run_attempt != "1":
        raise SimulationFundingError("funding run attempt must be 1")

    requests = report.get("requests")
    if isinstance(requests, bool) or not isinstance(requests, int) or not 1 <= requests <= 3:
        raise SimulationFundingError("funding request count is invalid")

    raw = report.get("observations")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise SimulationFundingError("funding observations are required")
    if report.get("observation_count") != len(raw):
        raise SimulationFundingError("funding observation_count mismatch")

    points: list[FundingPoint] = []
    previous_time: int | None = None
    for item in raw:
        if not isinstance(item, Mapping):
            raise SimulationFundingError("invalid funding observation")
        if item.get("symbol") != SYMBOL:
            raise SimulationFundingError("funding observation symbol mismatch")
        time_ms = item.get("funding_time_ms")
        rate = item.get("funding_rate")
        if isinstance(time_ms, bool) or not isinstance(time_ms, int):
            raise SimulationFundingError("funding timestamp is invalid")
        if not START_MS <= time_ms < END_MS:
            raise SimulationFundingError("funding timestamp outside fixed window")
        if previous_time is not None and time_ms <= previous_time:
            raise SimulationFundingError("funding timestamps must be strictly increasing")
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate):
            raise SimulationFundingError("funding rate is not finite")
        points.append(FundingPoint(SYMBOL, time_ms, float(rate)))
        previous_time = time_ms

    if report.get("first_time_ms") != points[0].time_ms:
        raise SimulationFundingError("funding first_time_ms mismatch")
    if report.get("last_time_ms") != points[-1].time_ms:
        raise SimulationFundingError("funding last_time_ms mismatch")
    return tuple(points)


def run_readiness_with_verified_funding(
    parquet_by_interval: Mapping[str, bytes],
    kline_receipt: Mapping[str, object],
    funding_report: Mapping[str, object],
) -> dict[str, object]:
    """Exercise the canonical paper backtest with exact K-line and funding evidence.

    This prepared bridge validates the complete cost-input path but deliberately
    never emits FULL_SIMULATION_READY because production simulation-data
    admission remains a separate authority decision.
    """

    candles = load_verified_sample(parquet_by_interval, kline_receipt)
    funding_points = load_verified_funding(funding_report)
    plans = generate_plans(candles)
    if not plans:
        return {
            "status": "FUNDING_PIPELINE_NOT_EXERCISED_NO_SIGNAL",
            "data_ready": True,
            "funding_data_ready": True,
            "pipeline_exercised": False,
            "full_simulation_ready": False,
            "generated_plan_count": 0,
            "executed_trade_count": 0,
            "funding_observation_count": len(funding_points),
            "blockers": [
                "no_candle_derived_strategy_signal",
                "production_simulation_data_admission_not_authorized",
            ],
        }

    result = run_long_backtest(
        candles_by_symbol={SYMBOL: candles["15M"]},
        plans=plans,
        funding_points=funding_points,
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
        "status": (
            "FUNDING_PIPELINE_PASS_NOT_ADMITTED"
            if exercised
            else "FUNDING_PIPELINE_NOT_EXERCISED"
        ),
        "data_ready": True,
        "funding_data_ready": True,
        "pipeline_exercised": exercised,
        "full_simulation_ready": False,
        "generated_plan_count": len(plans),
        "executed_trade_count": len(result.trades),
        "rejected_plan_count": len(result.rejected_plans),
        "funding_observation_count": len(funding_points),
        "blockers": ["production_simulation_data_admission_not_authorized"],
        "result": result,
    }
