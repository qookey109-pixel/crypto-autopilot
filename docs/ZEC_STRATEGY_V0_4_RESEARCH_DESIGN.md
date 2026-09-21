# ZEC Strategy V0.4 — Regime Activation Research Design

Status date: 2026-09-21

Status: **PREPARED / DEVELOPMENT CONTRACT ONLY / NO EXECUTION AUTHORITY**

## Why V0.4 exists

ZEC V0.3 completed the full governed development matrix:

- 64 candidates;
- 4 chronological folds;
- 256 / 256 cells;
- all 64 candidates satisfied the minimum 30 realized trades per fold;
- zero candidates achieved a positive worst-fold return;
- selection result: `NO_ELIGIBLE_DEVELOPMENT_CANDIDATE`.

The V0.3 selection gate is therefore preserved. V0.4 does not lower the
worst-fold threshold, reduce the trade-count floor, weaken stable-neighbor
requirements or promote the V0.3 diagnostic leader.

The V0.3 aggregate diagnostic instead points to a structural question: whether
the long-only MACD family should be **inactive during unsuitable market
regimes**.

At the frozen 1% risk budget, all 16 V0.3 signal configurations were negative in
the first two annual folds, while all 16 were positive in the final annual
fold. That pattern is more consistent with regime dependence than with an
activity shortage.

## Research question

> Can a small causal 4h bull-regime activation layer suppress the loss-making
> historical regimes enough for the same long-only 30m MACD family to become
> positive in every annual development fold?

This is a new development iteration on already-seen history. It is not a claim
that the V0.3 diagnostic leader was valid.

## Degrees-of-freedom reduction

V0.3 varied five axes. V0.4 intentionally removes most of them.

### Fixed at V0.3 development-derived values

The following values are fixed, not swept:

- volatility filter: `ATR_ROLLING_EXTREME_GUARD`;
- stop: `VOL_STOP_2_5ATR_BB_HALF`;
- account risk: 1% of current equity;
- maximum leverage: 3x;
- no averaging down, martingale or pyramiding.

These choices had directionally better aggregate return/drawdown behavior in
V0.3, but they are **not validated winners**. They are fixed only to reduce
research degrees of freedom.

The V0.3 risk axis is removed because entry/trade counts were exactly invariant
across the four risk values for every signal/fold group. Higher risk mainly
magnified loss and drawdown, so sizing is not treated as a signal-edge axis in
V0.4.

### MACD axis retained

Both prior MACD variants remain:

1. 12 / 26 / 9
2. 12 / 30 / 7

V0.3 aggregate evidence did not establish a robust winner between them.

## Causal 4h activation regimes

Every 30m bullish MACD crossover must use only the most recent 4h snapshot that
was already available when the closed 30m decision bar became usable.

No future 4h candle may be attached to an earlier decision.

### `TREND_STRICT_BASELINE`

This reproduces the V0.3 strict trend gate:

- 4h close > EMA200;
- EMA20 > EMA50;
- EMA20 slope / ATR > 0.

### `TREND_STACKED`

Adds one natural trend-stack condition:

- all baseline conditions;
- EMA50 > EMA200.

No arbitrary distance threshold is introduced.

### `TREND_STACKED_MOMENTUM`

Adds sign-based momentum confirmation using indicators already implemented in
the repository:

- all `TREND_STACKED` conditions;
- RSI14 > 50;
- 4h MACD histogram > 0.

The thresholds are natural center/sign boundaries rather than optimized ZEC
levels.

## Candidate matrix

The only sweep axes are:

- 2 MACD variants;
- 3 activation regimes.

Total: **6 candidates**.

The four frozen chronological development folds are unchanged, so the complete
matrix contains **24 cells**.

Selective omission is forbidden.

## Development and fresh-confirmation boundary

Development remains the already-seen interval:

`2022-08-01T00:00:00Z <= t < 2026-08-01T00:00:00Z`

with the same four annual folds used by V0.3.

The still-unopened fresh-confirmation interval remains:

`2026-08-01T00:00:00Z <= t < 2026-09-16T00:00:00Z`

V0.4 does not authorize reading that interval.

## Selection policy

V0.4 reuses the exact frozen V0.3 selection policy, canonical SHA-256:

`6484f59ee6e71156c776bfe43cdf8c4716dae74f936a164e8702e175c731250d`

The important boundaries therefore remain:

- at least 30 realized trades in every development fold;
- worst-fold return must be strictly positive;
- robust-first ranking;
- at least two independently eligible stable neighbors;
- a stable neighbor must retain at least 75% of the leader's worst-fold return;
- complete matrix required;
- fresh confirmation cannot select or reselect a candidate.

A V0.4 candidate that fails these rules is rejected. The policy is not relaxed
because V0.3 failed.

## Evidence lineage

The aggregate-only V0.3 diagnostic is frozen in:

`research/receipts/2026-09-21-zec-v0-3-development-diagnostic-v0-1.json`

It contains no raw candles and no raw trade list.

## What V0.4 does not test

This preregistration deliberately does not add:

- short execution;
- daily or cross-market regime data;
- BTC dominance / TOTAL3 / alt breadth as a trade gate;
- new MACD parameter optimization;
- trailing-stop optimization;
- time-stop optimization;
- risk-budget optimization;
- leverage optimization;
- L2/order-flow features;
- LLM-generated numeric signals.

Those may be separate future hypotheses, not hidden additions to this matrix.

## Authority

This design authorizes only offline contract validation.

It does **not** authorize:

- historical execution;
- provider/network reads;
- new data acquisition;
- R2 reads or writes;
- fresh confirmation;
- formal holdout access;
- source switching;
- model or strategy promotion;
- a formal trade plan;
- real-money orders;
- live trading.

A separate versioned execution authority would be required before any 24-cell
historical development run.
