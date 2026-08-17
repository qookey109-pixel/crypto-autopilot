from __future__ import annotations

from dataclasses import dataclass

from .models import RiskDecision


@dataclass(frozen=True, slots=True)
class RiskConfig:
    risk_fraction_per_trade: float = 0.01
    max_leverage: float = 3.0
    daily_loss_limit_r: float = 3.0
    max_new_trades_per_day: int = 3


def size_long_trade(
    *,
    equity_usd: float,
    entry_price: float,
    stop_price: float,
    realized_daily_r: float = 0.0,
    new_trades_today: int = 0,
    config: RiskConfig = RiskConfig(),
) -> RiskDecision:
    """Size a LONG position from risk budget, never from desired leverage."""
    if equity_usd <= 0:
        return RiskDecision(False, "invalid_equity")
    if entry_price <= 0 or stop_price <= 0 or stop_price >= entry_price:
        return RiskDecision(False, "invalid_long_stop")
    if realized_daily_r <= -config.daily_loss_limit_r:
        return RiskDecision(False, "daily_loss_gate")
    if new_trades_today >= config.max_new_trades_per_day:
        return RiskDecision(False, "daily_trade_count_gate")

    stop_distance_fraction = (entry_price - stop_price) / entry_price
    risk_usd = equity_usd * config.risk_fraction_per_trade
    notional_usd = risk_usd / stop_distance_fraction
    required_leverage = notional_usd / equity_usd

    if required_leverage > config.max_leverage:
        return RiskDecision(
            False,
            "required_leverage_exceeds_cap",
            round(risk_usd, 8),
            round(notional_usd, 8),
            round(required_leverage, 8),
        )

    return RiskDecision(
        True,
        "approved",
        round(risk_usd, 8),
        round(notional_usd, 8),
        round(required_leverage, 8),
    )
