from __future__ import annotations

from dataclasses import asdict

from crypto_autopilot.backtest import BacktestConfig, FundingPoint, LongTradePlan, run_long_backtest
from crypto_autopilot.models import Candle


INTERVAL_MS = 15 * 60 * 1000
START_TIME_MS = 1_704_067_200_000  # 2024-01-01T00:00:00Z; synthetic fixture only.
SYMBOL = "BTC_USDT_PERP"


def _candle(
    index: int,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> Candle:
    return Candle(
        time_ms=START_TIME_MS + index * INTERVAL_MS,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def build_demo_payload() -> dict[str, object]:
    """Run a deterministic synthetic paper simulation and return its audit payload.

    Trade plans are explicit fixture inputs. This function does not infer plans,
    request provider data, read R2, access a holdout, or submit an exchange order.
    """

    candles = [
        _candle(0, open_=100, high=101, low=99, close=100, volume=1_000),
        _candle(1, open_=100, high=102, low=99, close=101, volume=1_100),
        _candle(2, open_=101, high=106, low=100, close=105, volume=1_400),
        _candle(3, open_=105, high=106, low=104, close=105, volume=1_050),
        _candle(4, open_=104, high=105, low=99, close=100, volume=1_600),
        _candle(5, open_=100, high=103, low=99, close=102, volume=1_150),
        _candle(6, open_=102, high=105, low=101, close=104, volume=1_250),
        _candle(7, open_=104, high=106, low=103, close=105, volume=1_300),
    ]
    plans = [
        LongTradePlan(
            plan_id="demo-target",
            symbol=SYMBOL,
            signal_time_ms=candles[0].time_ms,
            stop_price=95.0,
            target_price=105.0,
        ),
        LongTradePlan(
            plan_id="demo-stop",
            symbol=SYMBOL,
            signal_time_ms=candles[2].time_ms,
            stop_price=100.0,
            target_price=115.0,
        ),
        LongTradePlan(
            plan_id="demo-end-of-data",
            symbol=SYMBOL,
            signal_time_ms=candles[4].time_ms,
            stop_price=96.0,
            target_price=112.0,
        ),
    ]
    funding = [
        FundingPoint(SYMBOL, candles[2].time_ms, 0.0001),
        FundingPoint(SYMBOL, candles[4].time_ms, 0.0001),
        FundingPoint(SYMBOL, candles[6].time_ms, -0.00005),
    ]
    config = BacktestConfig(
        initial_equity_usd=10_000.0,
        taker_fee_bps=5.0,
        slippage_bps=2.0,
    )
    result = run_long_backtest(
        candles_by_symbol={SYMBOL: candles},
        plans=plans,
        funding_points=funding,
        config=config,
    )

    return {
        "schema": "paper-simulation-demo-v0.1",
        "status": "PASS",
        "mode": "PAPER_ONLY",
        "data_class": "SYNTHETIC_FIXTURE",
        "interpretation": (
            "Execution and risk lifecycle demonstration only; this is not historical "
            "strategy performance or evidence of future profitability."
        ),
        "authority": {
            "trade_plans_auto_generated": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
            "provider_requests_performed": 0,
            "r2_reads_performed": False,
            "r2_writes_performed": False,
            "holdout_candles_accessed": False,
            "holdout_evaluated": False,
        },
        "assumptions": {
            "symbol": SYMBOL,
            "interval": "15M",
            "candle_count": len(candles),
            "explicit_plan_count": len(plans),
            "initial_equity_usd": config.initial_equity_usd,
            "risk_fraction_per_trade": config.risk.risk_fraction_per_trade,
            "maximum_leverage": config.risk.max_leverage,
            "maximum_new_trades_per_day": config.risk.max_new_trades_per_day,
            "taker_fee_bps_each_side": config.taker_fee_bps,
            "adverse_slippage_bps_each_fill": config.slippage_bps,
            "same_bar_stop_target_policy": "STOP_FIRST",
            "entry_policy": "FIRST_LATER_CANDLE_OPEN",
        },
        "metrics": asdict(result.metrics),
        "initial_equity_usd": result.initial_equity_usd,
        "final_equity_usd": result.final_equity_usd,
        "equity_curve": list(result.equity_curve),
        "trades": [asdict(trade) for trade in result.trades],
        "rejected_plans": [list(item) for item in result.rejected_plans],
        "event_count": len(result.events),
    }
