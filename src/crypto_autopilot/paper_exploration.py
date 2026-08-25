"""High-sample, independent paper replays for research evidence only."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Sequence

from .backtest import (
    BacktestConfig,
    BacktestTrade,
    FundingPoint,
    LongTradePlan,
    run_long_backtest,
)
from .models import Candle
from .risk import RiskConfig


@dataclass(frozen=True, slots=True)
class PaperExplorationConfig:
    max_samples_per_utc_day: int = 12
    max_samples_per_symbol_per_utc_day: int = 2
    risk_fraction_per_sample: float = 0.0025
    initial_equity_usd: float = 10_000.0
    max_leverage: float = 3.0
    taker_fee_bps: float = 5.0
    slippage_bps: float = 2.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_samples_per_utc_day <= 24:
            raise ValueError("exploration daily sample cap must be between 1 and 24")
        if not 1 <= self.max_samples_per_symbol_per_utc_day <= 4:
            raise ValueError("exploration per-symbol daily cap must be between 1 and 4")
        if self.max_samples_per_symbol_per_utc_day > self.max_samples_per_utc_day:
            raise ValueError("per-symbol exploration cap exceeds the total daily cap")
        if not 0 < self.risk_fraction_per_sample <= 0.005:
            raise ValueError("exploration risk fraction must be at most 0.5%")
        if self.initial_equity_usd <= 0 or not 0 < self.max_leverage <= 3.0:
            raise ValueError("exploration equity or leverage is outside the safe bound")
        if self.taker_fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("exploration costs cannot be negative")


def _day_key(time_ms: int) -> str:
    return datetime.fromtimestamp(time_ms / 1000, tz=UTC).date().isoformat()


def _single_plan_config(config: PaperExplorationConfig) -> BacktestConfig:
    return BacktestConfig(
        initial_equity_usd=config.initial_equity_usd,
        taker_fee_bps=config.taker_fee_bps,
        slippage_bps=config.slippage_bps,
        risk=RiskConfig(
            risk_fraction_per_trade=config.risk_fraction_per_sample,
            max_leverage=config.max_leverage,
            daily_loss_limit_r=1_000_000.0,
            max_new_trades_per_day=1,
        ),
    )


def run_paper_exploration(
    *,
    candles_by_symbol: dict[str, Sequence[Candle]],
    plans: Sequence[LongTradePlan],
    funding_points: Sequence[FundingPoint] = (),
    config: PaperExplorationConfig = PaperExplorationConfig(),
) -> dict[str, object]:
    """Replay eligible plans independently to increase training sample count.

    Independent samples may overlap in time.  Their PnL is never compounded
    into a portfolio equity curve, preventing a high-throughput experiment
    from being mistaken for the governed V0.1 paper broker.
    """

    if len({plan.plan_id for plan in plans}) != len(plans):
        raise ValueError("exploration plan_id values must be unique")
    accepted: list[BacktestTrade] = []
    rejected: list[tuple[str, str]] = []
    by_day: dict[str, int] = {}
    by_symbol_day: dict[tuple[str, str], int] = {}
    replay_config = _single_plan_config(config)
    for plan in sorted(plans, key=lambda item: (item.signal_time_ms, item.symbol, item.plan_id)):
        result = run_long_backtest(
            candles_by_symbol={
                plan.symbol: tuple(candles_by_symbol.get(plan.symbol, ()))
            },
            plans=(plan,),
            funding_points=tuple(
                point for point in funding_points if point.symbol == plan.symbol
            ),
            config=replay_config,
        )
        if not result.trades:
            rejected.extend(result.rejected_plans or ((plan.plan_id, "no_trade"),))
            continue
        trade = result.trades[0]
        day = _day_key(trade.entry_time_ms)
        symbol_day = (trade.symbol, day)
        if by_day.get(day, 0) >= config.max_samples_per_utc_day:
            rejected.append((plan.plan_id, "exploration_daily_sample_gate"))
            continue
        if (
            by_symbol_day.get(symbol_day, 0)
            >= config.max_samples_per_symbol_per_utc_day
        ):
            rejected.append((plan.plan_id, "exploration_symbol_daily_sample_gate"))
            continue
        accepted.append(trade)
        by_day[day] = by_day.get(day, 0) + 1
        by_symbol_day[symbol_day] = by_symbol_day.get(symbol_day, 0) + 1

    wins = sum(trade.net_pnl_usd > 0 for trade in accepted)
    return {
        "schema": "paper-exploration-replay-v0.2",
        "status": "PASS",
        "mode": "INDEPENDENT_SHADOW_SAMPLES",
        "sample_count": len(accepted),
        "rejected_count": len(rejected),
        "win_rate": wins / len(accepted) if accepted else 0.0,
        "average_r_multiple": (
            sum(trade.r_multiple for trade in accepted) / len(accepted)
            if accepted
            else 0.0
        ),
        "total_fees_usd_independent": sum(trade.fees_usd for trade in accepted),
        "total_slippage_usd_independent": sum(
            trade.slippage_cost_usd for trade in accepted
        ),
        "samples": [asdict(trade) for trade in accepted],
        "rejected_plans": [list(item) for item in rejected],
        "limits": asdict(config),
        "interpretation": {
            "independent_samples_not_portfolio_equity": True,
            "overlapping_samples_allowed": True,
            "composite_equity_curve_authorized": False,
        },
        "authority": {
            "provider_reads_authorized": False,
            "r2_writes_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
