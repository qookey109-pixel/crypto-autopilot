from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from .models import RiskDecision


@dataclass(frozen=True, slots=True)
class RiskConfig:
    risk_fraction_per_trade: float = 0.01
    max_leverage: float = 3.0
    daily_loss_limit_r: float = 3.0
    max_new_trades_per_day: int = 3

    def __post_init__(self) -> None:
        values = (
            self.risk_fraction_per_trade,
            self.max_leverage,
            self.daily_loss_limit_r,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("risk configuration values must be finite")
        if self.risk_fraction_per_trade <= 0 or self.risk_fraction_per_trade > 1:
            raise ValueError("risk_fraction_per_trade must be in (0, 1]")
        if self.max_leverage <= 0:
            raise ValueError("max_leverage must be positive")
        if self.daily_loss_limit_r <= 0:
            raise ValueError("daily_loss_limit_r must be positive")
        if self.max_new_trades_per_day <= 0:
            raise ValueError("max_new_trades_per_day must be positive")


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
    numeric_inputs = (equity_usd, entry_price, stop_price, realized_daily_r)
    if not all(math.isfinite(value) for value in numeric_inputs):
        return RiskDecision(False, "non_finite_risk_input")
    if new_trades_today < 0:
        return RiskDecision(False, "invalid_trade_count")
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

    derived = (stop_distance_fraction, risk_usd, notional_usd, required_leverage)
    if not all(math.isfinite(value) and value > 0 for value in derived):
        return RiskDecision(False, "non_finite_risk_output")

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


@dataclass(frozen=True, slots=True)
class PositionSizingPolicy:
    """Research-only account-risk and feasibility policy.

    Stop placement is an upstream market/strategy decision. This policy sizes
    around the supplied stop and never tightens it merely to consume the full
    target risk budget.
    """

    risk_fraction_per_trade: float = 0.01
    max_leverage: float = 3.0
    daily_loss_limit_r: float = 3.0
    max_new_positions_per_day: int = 3
    minimum_notional_usd: float = 0.0
    maximum_notional_usd: float | None = None

    def __post_init__(self) -> None:
        values = (
            self.risk_fraction_per_trade,
            self.max_leverage,
            self.daily_loss_limit_r,
            self.minimum_notional_usd,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("position sizing policy values must be finite")
        if self.maximum_notional_usd is not None and not math.isfinite(
            self.maximum_notional_usd
        ):
            raise ValueError("maximum_notional_usd must be finite when supplied")
        if not 0.0 < self.risk_fraction_per_trade <= 1.0:
            raise ValueError("risk_fraction_per_trade must be in (0, 1]")
        if self.max_leverage <= 0.0:
            raise ValueError("max_leverage must be positive")
        if self.daily_loss_limit_r <= 0.0:
            raise ValueError("daily_loss_limit_r must be positive")
        if self.max_new_positions_per_day <= 0:
            raise ValueError("max_new_positions_per_day must be positive")
        if self.minimum_notional_usd < 0.0:
            raise ValueError("minimum_notional_usd cannot be negative")
        if (
            self.maximum_notional_usd is not None
            and self.maximum_notional_usd <= 0.0
        ):
            raise ValueError("maximum_notional_usd must be positive when supplied")
        if (
            self.maximum_notional_usd is not None
            and self.maximum_notional_usd < self.minimum_notional_usd
        ):
            raise ValueError(
                "maximum_notional_usd cannot be below minimum_notional_usd"
            )


@dataclass(frozen=True, slots=True)
class PositionSizingPlan:
    status: str
    reason: str
    direction: str
    equity_usd: float
    entry_price: float
    stop_price: float
    stop_distance_fraction: float
    target_risk_usd: float
    realized_risk_usd: float
    target_notional_usd: float
    approved_notional_usd: float
    required_leverage: float
    realized_leverage: float
    risk_utilization_fraction: float
    clipped_by: tuple[str, ...]
    stop_preserved: bool = True


def _empty_position_sizing_plan(
    *,
    reason: str,
    direction: str,
    equity_usd: float,
    entry_price: float,
    stop_price: float,
) -> PositionSizingPlan:
    return PositionSizingPlan(
        status="NO_TRADE",
        reason=reason,
        direction=direction,
        equity_usd=equity_usd,
        entry_price=entry_price,
        stop_price=stop_price,
        stop_distance_fraction=0.0,
        target_risk_usd=0.0,
        realized_risk_usd=0.0,
        target_notional_usd=0.0,
        approved_notional_usd=0.0,
        required_leverage=0.0,
        realized_leverage=0.0,
        risk_utilization_fraction=0.0,
        clipped_by=(),
    )


def plan_position_size(
    *,
    direction: str,
    equity_usd: float,
    entry_price: float,
    stop_price: float,
    realized_daily_r: float = 0.0,
    new_positions_today: int = 0,
    policy: PositionSizingPolicy = PositionSizingPolicy(),
) -> PositionSizingPlan:
    """Produce a bounded research sizing plan for LONG or SHORT exposure.

    The target notional is derived from the supplied stop distance and account
    risk budget. Leverage/notional caps may reduce the approved notional and
    therefore realized risk, but the supplied stop is never tightened to force
    full risk deployment.
    """

    normalized_direction = direction.upper()
    numeric_inputs = (equity_usd, entry_price, stop_price, realized_daily_r)
    if normalized_direction not in {"LONG", "SHORT"}:
        return _empty_position_sizing_plan(
            reason="unsupported_direction",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if not all(math.isfinite(value) for value in numeric_inputs):
        return _empty_position_sizing_plan(
            reason="non_finite_risk_input",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if new_positions_today < 0:
        return _empty_position_sizing_plan(
            reason="invalid_position_count",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if equity_usd <= 0.0:
        return _empty_position_sizing_plan(
            reason="invalid_equity",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if entry_price <= 0.0 or stop_price <= 0.0:
        return _empty_position_sizing_plan(
            reason="invalid_price",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if normalized_direction == "LONG" and stop_price >= entry_price:
        return _empty_position_sizing_plan(
            reason="invalid_long_stop",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if normalized_direction == "SHORT" and stop_price <= entry_price:
        return _empty_position_sizing_plan(
            reason="invalid_short_stop",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if realized_daily_r <= -policy.daily_loss_limit_r:
        return _empty_position_sizing_plan(
            reason="daily_loss_gate",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )
    if new_positions_today >= policy.max_new_positions_per_day:
        return _empty_position_sizing_plan(
            reason="daily_position_count_gate",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )

    stop_distance_fraction = abs(entry_price - stop_price) / entry_price
    target_risk_usd = equity_usd * policy.risk_fraction_per_trade
    target_notional_usd = target_risk_usd / stop_distance_fraction
    required_leverage = target_notional_usd / equity_usd

    leverage_cap_notional = equity_usd * policy.max_leverage
    approved_notional_usd = min(target_notional_usd, leverage_cap_notional)
    clipped_by: list[str] = []
    if leverage_cap_notional < target_notional_usd:
        clipped_by.append("max_leverage")

    if (
        policy.maximum_notional_usd is not None
        and policy.maximum_notional_usd < approved_notional_usd
    ):
        approved_notional_usd = policy.maximum_notional_usd
        clipped_by.append("maximum_notional_usd")

    if approved_notional_usd < policy.minimum_notional_usd:
        return PositionSizingPlan(
            status="NO_TRADE",
            reason="minimum_notional_exceeds_safe_size",
            direction=normalized_direction,
            equity_usd=round(equity_usd, 8),
            entry_price=round(entry_price, 8),
            stop_price=round(stop_price, 8),
            stop_distance_fraction=round(stop_distance_fraction, 10),
            target_risk_usd=round(target_risk_usd, 8),
            realized_risk_usd=0.0,
            target_notional_usd=round(target_notional_usd, 8),
            approved_notional_usd=0.0,
            required_leverage=round(required_leverage, 8),
            realized_leverage=0.0,
            risk_utilization_fraction=0.0,
            clipped_by=tuple(clipped_by),
        )

    realized_risk_usd = approved_notional_usd * stop_distance_fraction
    realized_leverage = approved_notional_usd / equity_usd
    risk_utilization = realized_risk_usd / target_risk_usd

    derived = (
        stop_distance_fraction,
        target_risk_usd,
        realized_risk_usd,
        target_notional_usd,
        approved_notional_usd,
        required_leverage,
        realized_leverage,
        risk_utilization,
    )
    if not all(math.isfinite(value) and value >= 0.0 for value in derived):
        return _empty_position_sizing_plan(
            reason="non_finite_risk_output",
            direction=normalized_direction,
            equity_usd=equity_usd,
            entry_price=entry_price,
            stop_price=stop_price,
        )

    return PositionSizingPlan(
        status="SIZING_READY",
        reason="size_clipped_to_constraints" if clipped_by else "target_risk_fully_deployed",
        direction=normalized_direction,
        equity_usd=round(equity_usd, 8),
        entry_price=round(entry_price, 8),
        stop_price=round(stop_price, 8),
        stop_distance_fraction=round(stop_distance_fraction, 10),
        target_risk_usd=round(target_risk_usd, 8),
        realized_risk_usd=round(realized_risk_usd, 8),
        target_notional_usd=round(target_notional_usd, 8),
        approved_notional_usd=round(approved_notional_usd, 8),
        required_leverage=round(required_leverage, 8),
        realized_leverage=round(realized_leverage, 8),
        risk_utilization_fraction=round(risk_utilization, 8),
        clipped_by=tuple(clipped_by),
    )


def position_sizing_policy_from_config(
    payload: Mapping[str, object],
) -> PositionSizingPolicy:
    if payload.get("schema") != "qookey-risk-position-sizing-v0.1":
        raise ValueError("unsupported risk position sizing config")
    risk = payload.get("risk_budget")
    constraints = payload.get("constraints")
    if not isinstance(risk, Mapping) or not isinstance(constraints, Mapping):
        raise ValueError("risk_budget and constraints objects are required")

    numeric_fields = (
        risk.get("risk_fraction_per_trade"),
        risk.get("daily_loss_limit_r"),
        risk.get("max_new_positions_per_day"),
        constraints.get("max_leverage"),
        constraints.get("minimum_notional_usd"),
    )
    if any(isinstance(value, bool) for value in numeric_fields):
        raise ValueError("risk position sizing numeric fields cannot be booleans")
    maximum_notional = constraints.get("maximum_notional_usd")
    if isinstance(maximum_notional, bool):
        raise ValueError("maximum_notional_usd cannot be boolean")

    try:
        return PositionSizingPolicy(
            risk_fraction_per_trade=float(risk["risk_fraction_per_trade"]),
            max_leverage=float(constraints["max_leverage"]),
            daily_loss_limit_r=float(risk["daily_loss_limit_r"]),
            max_new_positions_per_day=int(risk["max_new_positions_per_day"]),
            minimum_notional_usd=float(constraints["minimum_notional_usd"]),
            maximum_notional_usd=(
                None if maximum_notional is None else float(maximum_notional)
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid risk position sizing config: {error}") from error
