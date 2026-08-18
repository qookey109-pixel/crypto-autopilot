# Technical Features V0.1

## Purpose

Technical Features V0.1 is the deterministic raw-indicator layer between audited historical candles and later strategy-feature construction.

It is deliberately **not** a strategy-parameter layer. It does not invent thresholds that are not frozen in `docs/STRATEGY_V0_1.md` or `config/strategy_v0_1.json`.

## Closed-bar authority

Pionex candle timestamps are treated as bar identity/start timestamps. A feature snapshot for a bar is not legal to consume until that bar has closed:

```text
available_at_ms = bar_time_ms + interval_ms
```

`closed_snapshots_as_of` and `latest_closed_snapshot` enforce this boundary.

A later strategy-replay layer may use the closed bar's `bar_time_ms` as the signal identity only after `available_at_ms` has been reached. The Backtest Engine then preserves its independent rule that the earliest possible fill is the next bar.

This two-boundary design prevents incomplete-bar and same-bar lookahead leakage.

## Input integrity

Before any indicator is calculated, the full input candle sequence must pass the existing candle audit for:

- duplicate timestamps,
- ordering,
- missing bars/gaps,
- timeframe alignment,
- OHLCV validity.

A failed audit raises `TechnicalDataError`. V0.1 never fills, interpolates or silently repairs missing candles.

## Frozen calculations

### EMA20 / EMA50

EMA uses:

```text
alpha = 2 / (period + 1)
```

The first EMA value is seeded by the simple average of the first `period` closes. Later values use the standard recursive EMA update.

### EMA20 slope

Raw one-bar slope:

```text
ema20_slope[t] = ema20[t] - ema20[t-1]
```

No normalization or minimum slope threshold is imposed in V0.1.

### ATR14

True Range is:

```text
max(
  high - low,
  abs(high - previous_close),
  abs(low - previous_close)
)
```

ATR14 is seeded with the arithmetic mean of the first 14 true ranges and then uses Wilder smoothing:

```text
atr[t] = (atr[t-1] * 13 + tr[t]) / 14
```

### Volume SMA20 and ratio

```text
volume_sma20 = mean(last 20 volumes)
volume_ratio = current_volume / volume_sma20
```

If the rolling volume average is zero, the ratio remains unavailable rather than inventing a value.

### Previous high

`previous_high` is the immediately preceding candle's high and is exposed as raw input for a later 15m continuation rule.

### ATR-normalized extension

When EMA20 and a positive ATR14 are available:

```text
extension_from_ema20_atr = (close - ema20) / atr14
```

This is a raw normalized distance only. It is **not** the strategy's `not_overextended` boolean.

## Warmup

A `TechnicalSnapshot.ready` value becomes true only when all baseline raw inputs required for later V0.1 setup/entry construction are available:

- EMA20,
- EMA50,
- EMA20 slope,
- ATR14,
- volume SMA20,
- volume ratio,
- previous high.

Because EMA50 has the longest current warmup, normal positive-volume data becomes ready at the 50th candle (zero-based index 49).

## Intentionally undefined strategy thresholds

The current strategy documents name the following concepts but do not freeze a numerical rule for them:

- excessive extension from EMA20,
- how close a pullback must come to EMA20,
- exact reclaim semantics,
- volume-confirmation multiplier,
- ATR buffer size for structural stop placement.

Technical Features V0.1 therefore does not output these booleans and does not choose values for them.

They must be introduced only through a versioned parameter definition and tested for stability rather than tuned to one sample.

## Determinism / anti-leakage tests

Regression coverage requires:

- exact closed-bar availability timing,
- future candle mutations cannot change past snapshots,
- gaps/duplicates are rejected without repair,
- correct warmup behavior,
- deterministic repeat output,
- raw extension remains separate from strategy gating.

## Boundaries

This module:

- does not modify or reproduce SState core,
- does not calculate historical SState probabilities,
- does not submit orders,
- does not use private Pionex API,
- does not authorize live trading,
- does not claim profitability.

It is research/backtest infrastructure only.
