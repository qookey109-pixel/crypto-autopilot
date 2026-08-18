from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import Candle
from .risk import RiskConfig, size_long_trade


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    initial_equity_usd: float = 10_000.0
    taker_fee_bps: float = 5.0
    slippage_bps: float = 2.0
    risk: RiskConfig = RiskConfig()
    conservative_same_bar_exit: bool = True

    def __post_init__(self) -> None:
        if self.initial_equity_usd <= 0:
            raise ValueError("initial_equity_usd must be positive")
        if self.taker_fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fee/slippage bps cannot be negative")


@dataclass(frozen=True, slots=True)
class LongTradePlan:
    """A strategy-approved LONG signal.

    `signal_time_ms` is the timestamp of the last fully-known bar. The engine
    never fills on that bar; the earliest allowed fill is the next candle open.
    """

    plan_id: str
    symbol: str
    signal_time_ms: int
    stop_price: float
    target_price: float

    def __post_init__(self) -> None:
        if not self.plan_id.strip() or not self.symbol.strip():
            raise ValueError("plan_id and symbol are required")
        if self.signal_time_ms < 0:
            raise ValueError("signal_time_ms cannot be negative")
        if self.stop_price <= 0 or self.target_price <= 0:
            raise ValueError("stop_price and target_price must be positive")
        if self.target_price <= self.stop_price:
            raise ValueError("target_price must be above stop_price")


@dataclass(frozen=True, slots=True)
class FundingPoint:
    symbol: str
    time_ms: int
    rate: float

    def __post_init__(self) -> None:
        if not self.symbol.strip() or self.time_ms < 0 or not math.isfinite(self.rate):
            raise ValueError("invalid funding point")


@dataclass(frozen=True, slots=True)
class BacktestEvent:
    sequence: int
    time_ms: int
    kind: str
    symbol: str
    plan_id: str
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    plan_id: str
    symbol: str
    signal_time_ms: int
    entry_time_ms: int
    exit_time_ms: int
    raw_entry_price: float
    entry_price: float
    raw_exit_price: float
    exit_price: float
    quantity: float
    risk_usd: float
    notional_usd: float
    gross_pnl_usd: float
    fees_usd: float
    funding_usd: float
    slippage_cost_usd: float
    net_pnl_usd: float
    r_multiple: float
    exit_reason: str


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float
    net_pnl_usd: float
    return_pct: float
    max_drawdown_pct: float
    profit_factor: float | None
    trade_sharpe: float | None
    total_fees_usd: float
    total_funding_usd: float
    total_slippage_cost_usd: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    initial_equity_usd: float
    final_equity_usd: float
    trades: tuple[BacktestTrade, ...]
    events: tuple[BacktestEvent, ...]
    rejected_plans: tuple[tuple[str, str], ...]
    equity_curve: tuple[float, ...]
    metrics: BacktestMetrics


def _r8(value: float) -> float:
    return round(float(value), 8)


def _day_key(time_ms: int) -> str:
    return datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc).date().isoformat()


def _validate_candles(candles: tuple[Candle, ...], symbol: str) -> None:
    previous: int | None = None
    for candle in candles:
        if previous is not None and candle.time_ms <= previous:
            raise ValueError(f"candles must be strictly increasing for {symbol}")
        previous = candle.time_ms
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"non-finite candle value for {symbol}")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0 or candle.volume < 0:
            raise ValueError(f"invalid candle value for {symbol}")
        if candle.low > min(candle.open, candle.close, candle.high):
            raise ValueError(f"invalid candle low for {symbol}")
        if candle.high < max(candle.open, candle.close, candle.low):
            raise ValueError(f"invalid candle high for {symbol}")


def _next_entry_index(candles: tuple[Candle, ...], signal_time_ms: int) -> int | None:
    for index, candle in enumerate(candles):
        if candle.time_ms > signal_time_ms:
            return index
    return None


def _exit_for_long(
    candles: tuple[Candle, ...],
    *,
    entry_index: int,
    stop_price: float,
    target_price: float,
    conservative_same_bar_exit: bool,
) -> tuple[int, float, str]:
    for candle in candles[entry_index:]:
        stop_hit = candle.low <= stop_price
        target_hit = candle.high >= target_price
        if stop_hit and target_hit:
            if conservative_same_bar_exit:
                return candle.time_ms, stop_price, "stop_same_bar_collision"
            return candle.time_ms, target_price, "target_same_bar_collision"
        if stop_hit:
            return candle.time_ms, stop_price, "stop"
        if target_hit:
            return candle.time_ms, target_price, "target"
    final = candles[-1]
    return final.time_ms, final.close, "end_of_data"


def _metrics(
    *,
    initial_equity: float,
    final_equity: float,
    trades: list[BacktestTrade],
    equity_curve: list[float],
) -> BacktestMetrics:
    wins = [trade for trade in trades if trade.net_pnl_usd > 0]
    losses = [trade for trade in trades if trade.net_pnl_usd < 0]
    gross_profit = sum(trade.net_pnl_usd for trade in wins)
    gross_loss = -sum(trade.net_pnl_usd for trade in losses)
    profit_factor = None if gross_loss == 0 else gross_profit / gross_loss

    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)

    r_values = [trade.r_multiple for trade in trades]
    trade_sharpe: float | None = None
    if len(r_values) >= 2:
        mean = sum(r_values) / len(r_values)
        variance = sum((value - mean) ** 2 for value in r_values) / (len(r_values) - 1)
        stdev = math.sqrt(variance)
        if stdev > 0:
            trade_sharpe = math.sqrt(len(r_values)) * mean / stdev

    count = len(trades)
    return BacktestMetrics(
        trade_count=count,
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=_r8(len(wins) / count if count else 0.0),
        net_pnl_usd=_r8(final_equity - initial_equity),
        return_pct=_r8((final_equity / initial_equity - 1.0) * 100.0),
        max_drawdown_pct=_r8(max_drawdown * 100.0),
        profit_factor=None if profit_factor is None else _r8(profit_factor),
        trade_sharpe=None if trade_sharpe is None else _r8(trade_sharpe),
        total_fees_usd=_r8(sum(trade.fees_usd for trade in trades)),
        total_funding_usd=_r8(sum(trade.funding_usd for trade in trades)),
        total_slippage_cost_usd=_r8(sum(trade.slippage_cost_usd for trade in trades)),
    )


def run_long_backtest(
    *,
    candles_by_symbol: dict[str, list[Candle] | tuple[Candle, ...]],
    plans: list[LongTradePlan] | tuple[LongTradePlan, ...],
    funding_points: list[FundingPoint] | tuple[FundingPoint, ...] = (),
    config: BacktestConfig = BacktestConfig(),
) -> BacktestResult:
    """Run a deterministic, paper-only LONG backtest.

    V0.1 intentionally supports one portfolio position at a time. Signals are
    treated as outputs of the existing strategy/SState boundary; this module
    does not reimplement SState or indicator production.
    """

    if len({plan.plan_id for plan in plans}) != len(plans):
        raise ValueError("plan_id values must be unique")

    prepared: dict[str, tuple[Candle, ...]] = {}
    for symbol, values in candles_by_symbol.items():
        candles = tuple(values)
        _validate_candles(candles, symbol)
        prepared[symbol] = candles

    funding_by_symbol: dict[str, list[FundingPoint]] = {}
    for point in sorted(funding_points, key=lambda item: (item.time_ms, item.symbol, item.rate)):
        funding_by_symbol.setdefault(point.symbol, []).append(point)

    ordered_plans = sorted(plans, key=lambda item: (item.signal_time_ms, item.symbol, item.plan_id))
    equity = config.initial_equity_usd
    equity_curve = [equity]
    trades: list[BacktestTrade] = []
    rejected: list[tuple[str, str]] = []
    events: list[BacktestEvent] = []
    sequence = 0
    portfolio_available_after_ms = -1
    realized_daily_r: dict[str, float] = {}
    new_trades_by_day: dict[str, int] = {}

    def emit(time_ms: int, kind: str, plan: LongTradePlan, **details: object) -> None:
        nonlocal sequence
        sequence += 1
        normalized = tuple(sorted((key, str(value)) for key, value in details.items()))
        events.append(BacktestEvent(sequence, time_ms, kind, plan.symbol, plan.plan_id, normalized))

    fee_rate = config.taker_fee_bps / 10_000.0
    slip_rate = config.slippage_bps / 10_000.0

    for plan in ordered_plans:
        emit(plan.signal_time_ms, "STRATEGY_SIGNAL", plan)
        candles = prepared.get(plan.symbol)
        if not candles:
            rejected.append((plan.plan_id, "missing_market_data"))
            emit(plan.signal_time_ms, "PLAN_REJECTED", plan, reason="missing_market_data")
            continue
        if plan.signal_time_ms < portfolio_available_after_ms:
            rejected.append((plan.plan_id, "position_overlap"))
            emit(plan.signal_time_ms, "PLAN_REJECTED", plan, reason="position_overlap")
            continue

        entry_index = _next_entry_index(candles, plan.signal_time_ms)
        if entry_index is None:
            rejected.append((plan.plan_id, "no_future_entry_bar"))
            emit(plan.signal_time_ms, "PLAN_REJECTED", plan, reason="no_future_entry_bar")
            continue

        entry_candle = candles[entry_index]
        raw_entry = entry_candle.open
        entry_price = raw_entry * (1.0 + slip_rate)
        if plan.target_price <= entry_price:
            rejected.append((plan.plan_id, "target_not_above_entry"))
            emit(entry_candle.time_ms, "PLAN_REJECTED", plan, reason="target_not_above_entry")
            continue

        entry_day = _day_key(entry_candle.time_ms)
        risk = size_long_trade(
            equity_usd=equity,
            entry_price=entry_price,
            stop_price=plan.stop_price,
            realized_daily_r=realized_daily_r.get(entry_day, 0.0),
            new_trades_today=new_trades_by_day.get(entry_day, 0),
            config=config.risk,
        )
        if not risk.approved:
            rejected.append((plan.plan_id, risk.reason))
            emit(entry_candle.time_ms, "RISK_REJECTED", plan, reason=risk.reason)
            continue

        emit(
            entry_candle.time_ms,
            "RISK_APPROVED",
            plan,
            risk_usd=risk.risk_usd,
            notional_usd=risk.notional_usd,
            required_leverage=risk.required_leverage,
        )
        emit(entry_candle.time_ms, "ORDER_INTENT", plan, side="LONG", notional_usd=risk.notional_usd)

        quantity = risk.notional_usd / entry_price
        emit(entry_candle.time_ms, "FILL_ENTRY", plan, price=_r8(entry_price), quantity=_r8(quantity))
        emit(entry_candle.time_ms, "POSITION_OPEN", plan)
        new_trades_by_day[entry_day] = new_trades_by_day.get(entry_day, 0) + 1

        exit_time, raw_exit, exit_reason = _exit_for_long(
            candles,
            entry_index=entry_index,
            stop_price=plan.stop_price,
            target_price=plan.target_price,
            conservative_same_bar_exit=config.conservative_same_bar_exit,
        )
        exit_price = raw_exit * (1.0 - slip_rate)
        gross_pnl = quantity * (exit_price - entry_price)
        entry_fee = quantity * entry_price * fee_rate
        exit_fee = quantity * exit_price * fee_rate
        fees = entry_fee + exit_fee
        funding = sum(
            risk.notional_usd * point.rate
            for point in funding_by_symbol.get(plan.symbol, [])
            if entry_candle.time_ms <= point.time_ms <= exit_time
        )
        slippage_cost = quantity * ((entry_price - raw_entry) + (raw_exit - exit_price))
        net_pnl = gross_pnl - fees - funding
        r_multiple = net_pnl / risk.risk_usd if risk.risk_usd else 0.0

        trade = BacktestTrade(
            plan_id=plan.plan_id,
            symbol=plan.symbol,
            signal_time_ms=plan.signal_time_ms,
            entry_time_ms=entry_candle.time_ms,
            exit_time_ms=exit_time,
            raw_entry_price=_r8(raw_entry),
            entry_price=_r8(entry_price),
            raw_exit_price=_r8(raw_exit),
            exit_price=_r8(exit_price),
            quantity=_r8(quantity),
            risk_usd=_r8(risk.risk_usd),
            notional_usd=_r8(risk.notional_usd),
            gross_pnl_usd=_r8(gross_pnl),
            fees_usd=_r8(fees),
            funding_usd=_r8(funding),
            slippage_cost_usd=_r8(slippage_cost),
            net_pnl_usd=_r8(net_pnl),
            r_multiple=_r8(r_multiple),
            exit_reason=exit_reason,
        )
        trades.append(trade)
        equity = _r8(equity + trade.net_pnl_usd)
        equity_curve.append(equity)
        exit_day = _day_key(exit_time)
        realized_daily_r[exit_day] = realized_daily_r.get(exit_day, 0.0) + trade.r_multiple
        portfolio_available_after_ms = exit_time

        emit(exit_time, "FILL_EXIT", plan, price=trade.exit_price, reason=exit_reason)
        emit(exit_time, "POSITION_CLOSED", plan)
        emit(exit_time, "PNL_REALIZED", plan, net_pnl_usd=trade.net_pnl_usd, r_multiple=trade.r_multiple)

    metrics = _metrics(
        initial_equity=config.initial_equity_usd,
        final_equity=equity,
        trades=trades,
        equity_curve=equity_curve,
    )
    return BacktestResult(
        initial_equity_usd=_r8(config.initial_equity_usd),
        final_equity_usd=_r8(equity),
        trades=tuple(trades),
        events=tuple(events),
        rejected_plans=tuple(rejected),
        equity_curve=tuple(_r8(value) for value in equity_curve),
        metrics=metrics,
    )
