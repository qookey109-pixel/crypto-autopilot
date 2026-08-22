# Technical Analysis Foundation V0.2

## Scope and authority

V0.2 is a deterministic feature-engineering and research layer. It produces
auditable evidence for future strategy, backtest, ML and paper-trading
consumers. It does not produce BUY/SELL labels, modify strategy thresholds,
authorize trade plans, access holdout or production R2 data, or authorize live
trading.

The existing V0.1 `TechnicalSnapshot` fields and `strategy.py` separation are
preserved. Technical calculations remain upstream of the existing strategy and
risk gates.

```text
provider candles
  -> candle audit (fail closed)
  -> technical indicators
  -> normalized feature fields
  -> market structure
  -> 4H / 60M / 15M snapshot
```

No provider requests are required by this layer. Callers supply already
obtained candles with their provider provenance preserved.

## Warmup and availability

Every candle must pass the existing `audit_candles` check. Missing candles,
duplicates, out-of-order data, misaligned timestamps and invalid OHLC values
raise `TechnicalDataError`; nothing is repaired or interpolated.

All indicators are calculated causally from the candle at the current index and
earlier candles only. A snapshot for a candle becomes consumable at
`bar_time_ms + INTERVAL_MS[interval]`, matching the existing closed-bar
semantics. `closed_snapshots_as_of` and the multi-timeframe builder use
`available_at_ms <= as_of_ms`; they never choose a future or nearest candle.

`TechnicalSnapshot.ready` preserves the V0.1 readiness contract. The new
`ready_v0_2` property additionally requires EMA200, RSI, complete MACD and
Bollinger values and all normalized fields. Warmup therefore remains explicit:
EMA200 needs 200 closes, RSI14 needs 14 price changes, MACD signal needs its
12/26/9 chain, and Bollinger needs 20 closes.

## Indicator definitions

- EMA20, EMA50 and EMA200 use an SMA seed over the period followed by the
  standard `2 / (period + 1)` recurrence.
- EMA20 slope is the current EMA20 minus the previous EMA20. The normalized
  value is `ema20_slope / atr14` when ATR is positive.
- EMA distance fractions are `(ema20 - ema50) / close` and
  `(ema50 - ema200) / close`.
- ATR14 keeps the existing Wilder true-range implementation. `atr14_fraction`
  is `atr14 / close`.
- RSI14 uses Wilder-smoothed gains and losses. The first output is available
  after 14 price changes. A flat series is defined as RSI 50; all-gain and
  all-loss windows are 100 and 0 respectively.
- MACD uses EMA12, EMA26 and EMA9 signal. Histogram is
  `macd - macd_signal`. MACD is evidence only and is never a trade trigger.
- Bollinger bands use a 20-close moving mean and population standard deviation
  with multiplier 2.0. Bandwidth is `(upper - lower) / mid`; position is
  `(close - lower) / (upper - lower)`. Zero denominators return `None`.
- Volume SMA20 and volume ratio retain the V0.1 definitions.

## Market structure

`build_market_structure_series` uses a 20-bar trailing previous range. The
current candle is excluded from that range. Breakout and breakdown booleans
compare the current close with that prior range; range values are `None` during
warmup.

Swing confirmation uses strict left/right windows (`left=2`, `right=2` by
default). A pivot at candle N is not visible at N. It is checked only when
candle N+2 closes, and the confirmed flag is emitted at N+2 with the pivot
price carried as the most recent confirmed level. Equal highs/lows are not
classified as pivots. Structure state is `UP` only when the latest confirmed
high and low are both higher than their previous confirmed counterparts, `DOWN`
when both are lower, `RANGE` otherwise once both histories exist, and
`INDETERMINATE` during confirmation warmup.

Because each output row reads at most through its own candle, mutating a future
candle cannot change an already available past row.

## Multi-timeframe alignment

`build_multi_timeframe_snapshot` accepts repository-native `4H`, `60M` and
`15M` candle sequences and returns one `MultiTimeframeTechnicalSnapshot` with
`four_hour`, `one_hour` and `fifteen_minute` components. Missing intervals make
the snapshot non-ready; no interval is substituted. Each component is selected
only when its own `available_at_ms` is no later than `as_of_ms`. Full readiness
requires all three components to be warmed up and structurally ready.

## Explicit non-authorities and limitations

- No strategy threshold, score weight, leverage, stop, entry or exit rule is
  changed by V0.2.
- No indicator is a BUY/SELL shortcut.
- No production R2, replacement holdout, V0.10 execution path, provider
  metadata capture, or live/private exchange API is accessed.
- The structure state is a deterministic descriptive feature, not a
  profitability-selected signal.
- ADX, stochastic, Ichimoku, Fibonacci, candlestick pattern mining, ML,
  sentiment, on-chain and order-book features are deferred.
