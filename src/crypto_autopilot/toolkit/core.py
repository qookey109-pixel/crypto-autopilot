from __future__ import annotations

from dataclasses import asdict
from typing import Any

from crypto_autopilot.backtest import (
    BacktestConfig,
    FundingPoint,
    LongTradePlan,
    run_long_backtest,
)
from crypto_autopilot.models import (
    Candle,
    EntryFeatures,
    OpportunityInput,
    SStateContext,
    SetupFeatures,
)
from crypto_autopilot.risk import RiskConfig, size_long_trade
from crypto_autopilot.strategy import evaluate_opportunity
from crypto_autopilot.technical import build_technical_series

from .registry import SAFETY_BOUNDARY, list_capabilities


def _candle_from_mapping(item: dict[str, Any]) -> Candle:
    return Candle(
        time_ms=int(item["time_ms"]),
        open=float(item["open"]),
        high=float(item["high"]),
        low=float(item["low"]),
        close=float(item["close"]),
        volume=float(item["volume"]),
    )


def _risk_config(values: dict[str, Any] | None = None) -> RiskConfig:
    if not values:
        return RiskConfig()
    return RiskConfig(
        risk_fraction_per_trade=float(
            values.get("risk_fraction_per_trade", RiskConfig.risk_fraction_per_trade)
        ),
        max_leverage=float(values.get("max_leverage", RiskConfig.max_leverage)),
        daily_loss_limit_r=float(
            values.get("daily_loss_limit_r", RiskConfig.daily_loss_limit_r)
        ),
        max_new_trades_per_day=int(
            values.get("max_new_trades_per_day", RiskConfig.max_new_trades_per_day)
        ),
    )


def get_indicators(
    candles: list[dict[str, Any]],
    *,
    interval: str,
    include_series: bool = False,
) -> dict[str, Any]:
    prepared = tuple(_candle_from_mapping(item) for item in candles)
    series = build_technical_series(prepared, interval)
    latest = None if not series else asdict(series[-1])
    response: dict[str, Any] = {
        "schema": "qookey-crypto-toolkit-indicators-v0.1",
        "status": "PASS",
        "interval": interval,
        "candle_count": len(prepared),
        "snapshot_count": len(series),
        "latest": latest,
        "latest_ready": bool(series and series[-1].ready),
        "latest_ready_v0_2": bool(series and series[-1].ready_v0_2),
        "authority": dict(SAFETY_BOUNDARY),
    }
    if include_series:
        response["series"] = [asdict(snapshot) for snapshot in series]
    return response


def evaluate_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    sstate = payload["sstate"]
    setup = payload["setup"]
    entry = payload["entry"]
    opportunity = OpportunityInput(
        symbol=str(payload["symbol"]),
        sstate=SStateContext(
            state=str(sstate["state"]),
            probability=(
                None if sstate.get("probability") is None else float(sstate["probability"])
            ),
            samples=int(sstate["samples"]),
            available=bool(sstate.get("available", True)),
        ),
        setup=SetupFeatures(
            ema20_above_ema50=bool(setup["ema20_above_ema50"]),
            ema20_slope_positive=bool(setup["ema20_slope_positive"]),
            close_above_ema20=bool(setup["close_above_ema20"]),
            not_overextended=bool(setup["not_overextended"]),
        ),
        entry=EntryFeatures(
            pullback_seen=bool(entry["pullback_seen"]),
            reclaimed_ema20=bool(entry["reclaimed_ema20"]),
            broke_previous_high=bool(entry["broke_previous_high"]),
            volume_confirmed=bool(entry["volume_confirmed"]),
        ),
        reward_risk=float(payload["reward_risk"]),
        liquidity_ok=bool(payload["liquidity_ok"]),
        funding_ok=bool(payload["funding_ok"]),
    )
    decision = evaluate_opportunity(
        opportunity,
        minimum_probability=float(payload.get("minimum_probability", 0.60)),
        minimum_samples=int(payload.get("minimum_samples", 50)),
        minimum_score=float(payload.get("minimum_score", 80.0)),
    )
    return {
        "schema": "qookey-crypto-toolkit-strategy-v0.1",
        "status": "PASS",
        "decision": asdict(decision),
        "authority": dict(SAFETY_BOUNDARY),
    }


def size_long_trade_tool(payload: dict[str, Any]) -> dict[str, Any]:
    decision = size_long_trade(
        equity_usd=float(payload["equity_usd"]),
        entry_price=float(payload["entry_price"]),
        stop_price=float(payload["stop_price"]),
        realized_daily_r=float(payload.get("realized_daily_r", 0.0)),
        new_trades_today=int(payload.get("new_trades_today", 0)),
        config=_risk_config(payload.get("risk")),
    )
    return {
        "schema": "qookey-crypto-toolkit-risk-v0.1",
        "status": "PASS",
        "decision": asdict(decision),
        "authority": dict(SAFETY_BOUNDARY),
    }


def run_paper_backtest(payload: dict[str, Any]) -> dict[str, Any]:
    candles_by_symbol = {
        str(symbol): tuple(_candle_from_mapping(item) for item in candles)
        for symbol, candles in payload["candles_by_symbol"].items()
    }
    plans = tuple(
        LongTradePlan(
            plan_id=str(item["plan_id"]),
            symbol=str(item["symbol"]),
            signal_time_ms=int(item["signal_time_ms"]),
            stop_price=float(item["stop_price"]),
            target_price=float(item["target_price"]),
        )
        for item in payload["plans"]
    )
    funding_points = tuple(
        FundingPoint(
            symbol=str(item["symbol"]),
            time_ms=int(item["time_ms"]),
            rate=float(item["rate"]),
        )
        for item in payload.get("funding_points", ())
    )
    config_values = payload.get("config") or {}
    config = BacktestConfig(
        initial_equity_usd=float(config_values.get("initial_equity_usd", 10_000.0)),
        taker_fee_bps=float(config_values.get("taker_fee_bps", 5.0)),
        slippage_bps=float(config_values.get("slippage_bps", 2.0)),
        risk=_risk_config(config_values.get("risk")),
        conservative_same_bar_exit=bool(
            config_values.get("conservative_same_bar_exit", True)
        ),
        max_holding_minutes=(
            None
            if config_values.get("max_holding_minutes") is None
            else int(config_values["max_holding_minutes"])
        ),
        kill_switch_time_ms=(
            None
            if config_values.get("kill_switch_time_ms") is None
            else int(config_values["kill_switch_time_ms"])
        ),
    )
    result = run_long_backtest(
        candles_by_symbol=candles_by_symbol,
        plans=plans,
        funding_points=funding_points,
        config=config,
    )
    return {
        "schema": "qookey-crypto-toolkit-paper-backtest-v0.1",
        "status": "PASS",
        "mode": "PAPER_ONLY",
        "result": asdict(result),
        "authority": dict(SAFETY_BOUNDARY),
    }


__all__ = [
    "evaluate_strategy",
    "get_indicators",
    "list_capabilities",
    "run_paper_backtest",
    "size_long_trade_tool",
]
