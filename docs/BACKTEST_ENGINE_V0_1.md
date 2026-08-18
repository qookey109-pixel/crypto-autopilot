# Backtest Engine V0.1

## Scope

Backtest Engine V0.1 is a deterministic, paper-only execution simulator for the existing Qookey Crypto Autopilot strategy/risk boundaries.

It does **not** reimplement SState, does not calculate SState probabilities, does not authorize live trading, and does not submit private Pionex API requests.

## Event flow

The initial event contract is:

`StrategySignal -> RiskDecision -> OrderIntent -> Fill -> Position -> PnL`

`LongTradePlan` represents a strategy-approved LONG signal produced upstream. The existing `risk.size_long_trade` implementation remains the sizing authority.

## Anti-leakage execution rule

A signal timestamp represents the last fully-known candle. The engine is forbidden from filling on that same candle.

The earliest permitted entry is the **open of the first candle whose timestamp is strictly greater than the signal timestamp**.

If no later candle exists, the plan is rejected with `no_future_entry_bar` rather than receiving a synthetic fill.

This rule is intentionally conservative and is a permanent V0.1 anti-lookahead gate.

## Intrabar ambiguity

OHLC candles do not reveal whether the high or low happened first. If a LONG position's stop and target are both touched by the same candle, V0.1 assumes the adverse path and exits at the stop (`stop_same_bar_collision`).

This avoids optimistic hidden path assumptions.

## Portfolio scope

V0.1 permits one open portfolio position at a time. A signal generated while the prior position is still open is rejected as `position_overlap`.

This constraint can only be relaxed in a versioned revision with new tests and portfolio-risk rules.

## Costs

The engine models explicitly:

- taker fee in basis points on entry and exit notional,
- adverse entry/exit slippage in basis points,
- optional funding observations supplied as `FundingPoint` values.

A positive funding rate is a cost to the LONG position; a negative rate is a credit. V0.1 applies each supplied funding rate to entry notional. Funding data acquisition itself is not implemented here.

## Risk integration

The existing `RiskConfig` and `size_long_trade` path remain authoritative for:

- risk fraction per trade,
- leverage cap,
- daily realized-loss gate,
- maximum new trades per day.

The backtest engine must not bypass a rejected `RiskDecision`.

## Determinism

Given identical candles, plans, funding points, and config, the complete `BacktestResult` must be identical, including:

- fills,
- trade results,
- event ordering,
- rejected plans,
- equity curve,
- metrics.

No random slippage is used in V0.1.

## Metrics

V0.1 emits:

- trade count,
- wins/losses and win rate,
- net PnL and return,
- trade-close max drawdown,
- profit factor when losses exist,
- trade-level Sharpe-style statistic when sufficient variance exists,
- total fees,
- total funding,
- total modeled slippage cost.

These are research metrics only and are not live-trading authorization evidence.

## Explicit non-goals

V0.1 does not yet provide:

- indicator calculation,
- automatic conversion of raw candles into `OpportunityInput`,
- real SState historical output ingestion,
- partial fills/order-book simulation,
- liquidation modeling,
- mark-price-specific liquidation logic,
- portfolio concurrency,
- exchange-specific maker/taker tiers,
- funding-rate acquisition,
- live execution.

Those require separate versioned evidence.
