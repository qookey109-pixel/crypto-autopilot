from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Iterable, Sequence

from ..backtest import FundingPoint
from ..models import Candle


FIFTEEN_MINUTES_MS = 15 * 60 * 1000
THIRTY_MINUTES_MS = 30 * 60 * 1000


@dataclass(frozen=True, slots=True)
class BitgetMacdResearchConfig:
    """Paper-only research configuration for a 30m long MACD strategy.

    `fluctuation_*` is an explicit research approximation because Bitget's
    public documentation names the volatility filter but does not publish its
    exact formula. It is calculated from already-closed bars only.
    """

    symbol: str = "ZECUSDT"
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    stop_loss_fraction: float = 0.05
    leverage: float = 3.0
    margin_fraction: float = 0.20
    risk_cap_fraction: float | None = None
    fluctuation_lookback: int = 5
    min_fluctuation_fraction: float = 0.012
    taker_fee_bps_per_side: float = 6.0
    slippage_bps_per_side: float = 2.0

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not 1 <= self.fast_period < self.slow_period:
            raise ValueError("MACD periods must satisfy 1 <= fast < slow")
        if self.signal_period < 1:
            raise ValueError("signal_period must be positive")
        fractions = (
            self.stop_loss_fraction,
            self.margin_fraction,
            self.min_fluctuation_fraction,
        )
        if not all(math.isfinite(value) for value in fractions):
            raise ValueError("research fractions must be finite")
        if not 0 < self.stop_loss_fraction < 1:
            raise ValueError("stop_loss_fraction must be in (0, 1)")
        if not 0 < self.margin_fraction <= 1:
            raise ValueError("margin_fraction must be in (0, 1]")
        if self.leverage <= 0 or not math.isfinite(self.leverage):
            raise ValueError("leverage must be positive and finite")
        if self.risk_cap_fraction is not None:
            if not math.isfinite(self.risk_cap_fraction) or not 0 < self.risk_cap_fraction <= 1:
                raise ValueError("risk_cap_fraction must be in (0, 1] when set")
        if self.fluctuation_lookback < 0:
            raise ValueError("fluctuation_lookback cannot be negative")
        if self.min_fluctuation_fraction < 0:
            raise ValueError("min_fluctuation_fraction cannot be negative")
        costs = (self.taker_fee_bps_per_side, self.slippage_bps_per_side)
        if not all(math.isfinite(value) and value >= 0 for value in costs):
            raise ValueError("fee/slippage values must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class BitgetMacdResearchTrade:
    entry_time_ms: int
    exit_time_ms: int
    raw_entry_price: float
    entry_price: float
    raw_exit_price: float
    exit_price: float
    quantity: float
    notional_usd: float
    net_pnl_usd: float
    fees_usd: float
    funding_usd: float
    slippage_cost_usd: float
    exit_reason: str


@dataclass(frozen=True, slots=True)
class BitgetMacdResearchMetrics:
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float
    net_pnl_usd: float
    return_pct: float
    max_drawdown_pct: float
    profit_factor: float | None
    return_over_drawdown: float | None
    max_consecutive_losses: int
    total_fees_usd: float
    total_funding_usd: float
    total_slippage_cost_usd: float


@dataclass(frozen=True, slots=True)
class BitgetMacdResearchResult:
    config: BitgetMacdResearchConfig
    initial_equity_usd: float
    final_equity_usd: float
    trades: tuple[BitgetMacdResearchTrade, ...]
    equity_curve: tuple[float, ...]
    metrics: BitgetMacdResearchMetrics
    fluctuation_filter_semantics: str = "RESEARCH_APPROX_CLOSED_BAR_HIGH_LOW_RANGE_OVER_LAST_CLOSE"
    bitget_filter_formula_verified: bool = False
    paper_only: bool = True


def _r8(value: float) -> float:
    return round(float(value), 8)


def aggregate_15m_to_30m(candles: Sequence[Candle]) -> tuple[Candle, ...]:
    """Aggregate contiguous 15m candles into canonical UTC-aligned 30m bars.

    A partial leading or trailing half-hour is dropped. Any interior gap fails
    closed; no candle is interpolated or repaired.
    """

    source = tuple(candles)
    if not source:
        return ()
    previous_time: int | None = None
    for candle in source:
        if previous_time is not None and candle.time_ms - previous_time != FIFTEEN_MINUTES_MS:
            raise ValueError("15m candles must be strictly contiguous")
        previous_time = candle.time_ms
        prices = (candle.open, candle.high, candle.low, candle.close)
        if not all(math.isfinite(value) and value > 0 for value in prices):
            raise ValueError("invalid candle price")
        if not math.isfinite(candle.volume) or candle.volume < 0:
            raise ValueError("invalid candle volume")

    start = 0
    if source[0].time_ms % THIRTY_MINUTES_MS != 0:
        start = 1
    end = len(source)
    if (end - start) % 2:
        end -= 1

    output: list[Candle] = []
    for index in range(start, end, 2):
        first = source[index]
        second = source[index + 1]
        if first.time_ms % THIRTY_MINUTES_MS != 0:
            raise ValueError("30m aggregation requires UTC half-hour alignment")
        if second.time_ms != first.time_ms + FIFTEEN_MINUTES_MS:
            raise ValueError("30m aggregation requires exactly two contiguous 15m bars")
        output.append(
            Candle(
                time_ms=first.time_ms,
                open=first.open,
                high=max(first.high, second.high),
                low=min(first.low, second.low),
                close=second.close,
                volume=first.volume + second.volume,
            )
        )
    return tuple(output)


def _ema(values: Sequence[float], period: int) -> tuple[float | None, ...]:
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)
    seed = sum(values[:period]) / period
    output[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for index in range(period, len(values)):
        previous = (float(values[index]) - previous) * alpha + previous
        output[index] = previous
    return tuple(output)


def macd_series(
    candles: Sequence[Candle], *, fast_period: int, slow_period: int, signal_period: int
) -> tuple[tuple[float | None, ...], tuple[float | None, ...]]:
    closes = tuple(candle.close for candle in candles)
    fast = _ema(closes, fast_period)
    slow = _ema(closes, slow_period)
    macd: list[float | None] = [None] * len(closes)
    for index, (fast_value, slow_value) in enumerate(zip(fast, slow)):
        if fast_value is not None and slow_value is not None:
            macd[index] = fast_value - slow_value

    ready_values = tuple(value for value in macd if value is not None)
    signal_ready = _ema(ready_values, signal_period)
    signal: list[float | None] = [None] * len(closes)
    first_ready = next((i for i, value in enumerate(macd) if value is not None), len(closes))
    for offset, value in enumerate(signal_ready):
        if first_ready + offset < len(signal):
            signal[first_ready + offset] = value
    return tuple(macd), tuple(signal)


def research_fluctuation_fraction(
    candles: Sequence[Candle], index: int, lookback: int
) -> float | None:
    if lookback <= 0:
        return None
    if index + 1 < lookback:
        return None
    window = candles[index - lookback + 1 : index + 1]
    last_close = window[-1].close
    return (max(candle.high for candle in window) - min(candle.low for candle in window)) / last_close


def _crosses(
    macd: Sequence[float | None], signal: Sequence[float | None]
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    up = [False] * len(macd)
    down = [False] * len(macd)
    for index in range(1, len(macd)):
        previous = (macd[index - 1], signal[index - 1])
        current = (macd[index], signal[index])
        if None in previous or None in current:
            continue
        previous_macd, previous_signal = previous
        current_macd, current_signal = current
        assert previous_macd is not None and previous_signal is not None
        assert current_macd is not None and current_signal is not None
        up[index] = previous_macd <= previous_signal and current_macd > current_signal
        down[index] = previous_macd >= previous_signal and current_macd < current_signal
    return tuple(up), tuple(down)


def _position_notional(
    equity: float, entry_price: float, config: BitgetMacdResearchConfig
) -> float:
    margin_cap = equity * config.margin_fraction * config.leverage
    if config.risk_cap_fraction is None:
        return margin_cap
    risk_cap = equity * config.risk_cap_fraction / config.stop_loss_fraction
    return min(margin_cap, risk_cap)


def _metrics(
    initial_equity: float,
    final_equity: float,
    trades: Sequence[BitgetMacdResearchTrade],
    equity_curve: Sequence[float],
) -> BitgetMacdResearchMetrics:
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

    max_consecutive_losses = 0
    current_losses = 0
    for trade in trades:
        if trade.net_pnl_usd < 0:
            current_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, current_losses)
        else:
            current_losses = 0

    return_pct = (final_equity / initial_equity - 1.0) * 100.0
    max_drawdown_pct = max_drawdown * 100.0
    return_over_drawdown = None
    if max_drawdown_pct > 0:
        return_over_drawdown = return_pct / max_drawdown_pct

    count = len(trades)
    return BitgetMacdResearchMetrics(
        trade_count=count,
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=_r8(len(wins) / count if count else 0.0),
        net_pnl_usd=_r8(final_equity - initial_equity),
        return_pct=_r8(return_pct),
        max_drawdown_pct=_r8(max_drawdown_pct),
        profit_factor=None if profit_factor is None else _r8(profit_factor),
        return_over_drawdown=(
            None if return_over_drawdown is None else _r8(return_over_drawdown)
        ),
        max_consecutive_losses=max_consecutive_losses,
        total_fees_usd=_r8(sum(trade.fees_usd for trade in trades)),
        total_funding_usd=_r8(sum(trade.funding_usd for trade in trades)),
        total_slippage_cost_usd=_r8(sum(trade.slippage_cost_usd for trade in trades)),
    )


def run_bitget_macd_long_30m_research(
    *,
    candles_15m: Sequence[Candle],
    config: BitgetMacdResearchConfig = BitgetMacdResearchConfig(),
    funding_points: Sequence[FundingPoint] = (),
    initial_equity_usd: float = 10_000.0,
) -> BitgetMacdResearchResult:
    """Run a deterministic paper-only long MACD backtest from local candles."""

    if not math.isfinite(initial_equity_usd) or initial_equity_usd <= 0:
        raise ValueError("initial_equity_usd must be positive and finite")
    candles = aggregate_15m_to_30m(candles_15m)
    if len(candles) < config.slow_period + config.signal_period + 2:
        raise ValueError("not enough 30m candles for configured MACD warmup")

    macd, signal = macd_series(
        candles,
        fast_period=config.fast_period,
        slow_period=config.slow_period,
        signal_period=config.signal_period,
    )
    cross_up, cross_down = _crosses(macd, signal)
    fee_rate = config.taker_fee_bps_per_side / 10_000.0
    slip_rate = config.slippage_bps_per_side / 10_000.0
    funding = sorted(funding_points, key=lambda point: point.time_ms)

    equity = initial_equity_usd
    equity_curve = [equity]
    trades: list[BitgetMacdResearchTrade] = []
    signal_index = 1

    while signal_index < len(candles) - 1:
        if not cross_up[signal_index]:
            signal_index += 1
            continue
        if config.fluctuation_lookback > 0 and config.min_fluctuation_fraction > 0:
            fluctuation = research_fluctuation_fraction(
                candles, signal_index, config.fluctuation_lookback
            )
            if fluctuation is None or fluctuation < config.min_fluctuation_fraction:
                signal_index += 1
                continue

        entry_index = signal_index + 1
        entry_bar = candles[entry_index]
        raw_entry = entry_bar.open
        entry_price = raw_entry * (1.0 + slip_rate)
        stop_price = entry_price * (1.0 - config.stop_loss_fraction)
        notional = _position_notional(equity, entry_price, config)
        quantity = notional / entry_price

        exit_index = len(candles) - 1
        raw_exit = candles[-1].close
        exit_reason = "end_of_data"
        for index in range(entry_index, len(candles)):
            candle = candles[index]
            if candle.open <= stop_price:
                exit_index = index
                raw_exit = candle.open
                exit_reason = "stop_gap"
                break
            if candle.low <= stop_price:
                exit_index = index
                raw_exit = stop_price
                exit_reason = "stop"
                break
            if cross_down[index] and index + 1 < len(candles):
                exit_index = index + 1
                raw_exit = candles[exit_index].open
                exit_reason = "macd_death_cross_next_open"
                break

        exit_bar = candles[exit_index]
        exit_price = raw_exit * (1.0 - slip_rate)
        gross_pnl = quantity * (exit_price - entry_price)
        fees = quantity * entry_price * fee_rate + quantity * exit_price * fee_rate
        funding_usd = sum(
            notional * point.rate
            for point in funding
            if point.symbol == config.symbol
            and entry_bar.time_ms < point.time_ms <= exit_bar.time_ms
        )
        slippage_cost = quantity * (
            (entry_price - raw_entry) + (raw_exit - exit_price)
        )
        net_pnl = gross_pnl - fees - funding_usd
        trades.append(
            BitgetMacdResearchTrade(
                entry_time_ms=entry_bar.time_ms,
                exit_time_ms=exit_bar.time_ms,
                raw_entry_price=_r8(raw_entry),
                entry_price=_r8(entry_price),
                raw_exit_price=_r8(raw_exit),
                exit_price=_r8(exit_price),
                quantity=_r8(quantity),
                notional_usd=_r8(notional),
                net_pnl_usd=_r8(net_pnl),
                fees_usd=_r8(fees),
                funding_usd=_r8(funding_usd),
                slippage_cost_usd=_r8(slippage_cost),
                exit_reason=exit_reason,
            )
        )
        equity = _r8(equity + net_pnl)
        equity_curve.append(equity)
        if equity <= 0:
            break
        signal_index = max(exit_index, signal_index + 1)

    metrics = _metrics(initial_equity_usd, equity, trades, equity_curve)
    return BitgetMacdResearchResult(
        config=config,
        initial_equity_usd=_r8(initial_equity_usd),
        final_equity_usd=_r8(equity),
        trades=tuple(trades),
        equity_curve=tuple(_r8(value) for value in equity_curve),
        metrics=metrics,
    )


def default_bitget_macd_candidate_grid() -> tuple[BitgetMacdResearchConfig, ...]:
    """Curated sensitivity grid; research candidates, not strategy authority."""

    baseline = BitgetMacdResearchConfig()
    filters = ((0, 0.0), (3, 0.008), (5, 0.012), (8, 0.016))
    risk_profiles = (
        (3.0, 0.20, None),
        (3.0, 0.10, 0.01),
        (2.0, 0.15, 0.01),
    )
    configs: list[BitgetMacdResearchConfig] = []
    for fast in (8, 10, 12, 14):
        for slow in (21, 26, 30, 35):
            if fast >= slow:
                continue
            for signal in (5, 7, 9):
                for stop in (0.03, 0.04, 0.05, 0.06):
                    for lookback, fluctuation in filters:
                        for leverage, margin, risk_cap in risk_profiles:
                            configs.append(
                                replace(
                                    baseline,
                                    fast_period=fast,
                                    slow_period=slow,
                                    signal_period=signal,
                                    stop_loss_fraction=stop,
                                    leverage=leverage,
                                    margin_fraction=margin,
                                    risk_cap_fraction=risk_cap,
                                    fluctuation_lookback=lookback,
                                    min_fluctuation_fraction=fluctuation,
                                )
                            )
    return tuple(configs)


def run_candidate_grid(
    *,
    candles_15m: Sequence[Candle],
    configs: Iterable[BitgetMacdResearchConfig] | None = None,
    funding_points: Sequence[FundingPoint] = (),
    initial_equity_usd: float = 10_000.0,
) -> tuple[BitgetMacdResearchResult, ...]:
    candidates = tuple(configs) if configs is not None else default_bitget_macd_candidate_grid()
    return tuple(
        run_bitget_macd_long_30m_research(
            candles_15m=candles_15m,
            config=config,
            funding_points=funding_points,
            initial_equity_usd=initial_equity_usd,
        )
        for config in candidates
    )


def rank_candidates(
    results: Sequence[BitgetMacdResearchResult], *, min_trades: int = 20
) -> tuple[BitgetMacdResearchResult, ...]:
    """Rank transparently without claiming statistical proof or future profit."""

    def key(result: BitgetMacdResearchResult) -> tuple[float, ...]:
        metrics = result.metrics
        qualified = 1.0 if metrics.trade_count >= min_trades else 0.0
        profitable = 1.0 if (metrics.profit_factor or 0.0) > 1.0 else 0.0
        return_over_drawdown = metrics.return_over_drawdown or -1e9
        profit_factor = metrics.profit_factor or 0.0
        return (
            qualified,
            profitable,
            return_over_drawdown,
            profit_factor,
            metrics.return_pct,
            -metrics.max_drawdown_pct,
            float(metrics.trade_count),
        )

    return tuple(sorted(results, key=key, reverse=True))


def result_summary(result: BitgetMacdResearchResult) -> dict[str, object]:
    return {
        "config": asdict(result.config),
        "metrics": asdict(result.metrics),
        "final_equity_usd": result.final_equity_usd,
        "paper_only": result.paper_only,
        "fluctuation_filter_semantics": result.fluctuation_filter_semantics,
        "bitget_filter_formula_verified": result.bitget_filter_formula_verified,
    }
