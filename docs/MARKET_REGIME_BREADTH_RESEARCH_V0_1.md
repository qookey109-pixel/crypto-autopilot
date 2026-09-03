# Market Regime / Altcoin Breadth Research V0.1

Status: **PREPARED / RESEARCH ONLY / NO DATA-FETCH OR TRADING AUTHORITY**

This layer turns broad crypto-market context into causal descriptive evidence.
It does not replace the existing strategy, SState, V0.6 Shadow regime slices,
or Failed Breakout Research V0.1.

## Why this layer exists

A BTC uptrend does not imply that the broader altcoin market is healthy. A move
can be concentrated in BTC while ETH/BTC weakens and only a minority of alts
participate. Conversely, an expanding altcoin market should be visible across
several independent dimensions rather than from one chart level.

V0.1 therefore keeps these dimensions separate:

1. BTC return over a fixed trailing window;
2. aggregate crypto market capitalization excluding BTC and ETH (the semantic
   equivalent commonly charted as TOTAL3), measured by trailing return;
3. BTC dominance, measured by trailing percentage-point change;
4. ETH/BTC relative strength, derived from synchronized closed BTC and ETH
   prices;
5. equal-weight altcoin breadth from a fixed aligned market universe.

No absolute BTC, TOTAL3 or dominance price/level is a parameter. Livestream or
KOL levels such as a specific BTC price or a specific TOTAL3 market-cap target
may be preserved as timestamped forecast evidence elsewhere, but they cannot be
hardcoded into this research classifier.

## Relationship to existing research

V0.6 Shadow already contains ATR, ADX and volume regime slices. Those describe
conditions *inside one market/dataset*. This V0.1 layer is different: it
measures *cross-market participation and concentration*.

Failed Breakout Research V0.1 asks whether a range break is accepted or rejected.
This layer can eventually be evaluated beside that evidence. For example, a
breakout occurring during `ALT_EXPANSION` may behave differently from one during
`BTC_CONCENTRATION`, but V0.1 does not assume that relationship is profitable.
It must be tested independently.

## Fixed-universe breadth

`build_alt_breadth_series()` accepts an already available map of symbol to
closed candles. It performs no network access.

The breadth contract is deliberately strict:

- BTC and ETH are excluded from the alt basket by default;
- at least 20 alt markets are required;
- every included market must share the exact same timestamp grid;
- all candle series are audited through the existing technical-data path;
- missing bars are not filled or interpolated;
- membership is fixed for one research run;
- each market receives equal weight;
- `above_ema20_ratio` is the fraction of the fixed universe closing above its
  causal EMA20;
- `positive_momentum_ratio` is the fraction whose close is above the close five
  bars earlier.

This avoids silently turning survivorship repair, missing-data repair or
market-cap weighting into hidden model choices.

## Cross-market observations

`MarketRegimeObservation` is an aligned input record containing:

- closed BTC price;
- closed ETH price;
- BTC/ETH-excluded aggregate crypto market cap;
- BTC dominance percent;
- the two breadth ratios;
- the earliest timestamp at which the complete aligned record was available.

V0.1 intentionally does **not** implement a provider fetcher for aggregate
market cap or BTC dominance. The metric semantics are defined, but the source
must be separately selected, recorded and authorized. A charting-vendor symbol
is not silently treated as data authority.

## Descriptive states

After a 20-bar warm-up, the layer records five yes/no evidence votes for each
candidate regime. A state requires at least four of five votes and must be the
unique winner; otherwise the state is `MIXED`.

### `ALT_EXPANSION`

Evidence votes:

- BTC/ETH-excluded aggregate market cap return > 0;
- BTC dominance change < 0;
- ETH/BTC return > 0;
- more than 50% of the fixed alt universe is above EMA20;
- more than 50% of the fixed alt universe has positive five-bar momentum.

### `BTC_CONCENTRATION`

Evidence votes:

- BTC return > 0;
- BTC dominance change > 0;
- ETH/BTC return < 0;
- fewer than 50% of alts are above EMA20;
- aggregate ex-BTC/ETH market-cap return is below BTC return.

### `BROAD_RISK_OFF`

Evidence votes:

- BTC return < 0;
- aggregate ex-BTC/ETH market-cap return < 0;
- ETH/BTC return < 0;
- fewer than 50% of alts are above EMA20;
- fewer than 50% of alts have positive five-bar momentum.

Before the trailing window is ready, the state is `INSUFFICIENT`.

## Causality and leakage boundary

- all price/breadth inputs must come from closed bars;
- the observation `available_at_ms` must represent when all inputs were actually
  available, not merely the nominal bar timestamp;
- `latest_market_regime_as_of()` cannot return future snapshots;
- exact aligned bar cadence is required;
- the replacement holdout remains unopened and cannot tune the 20-bar lookback,
  5-bar momentum, 50% majority or 4-of-5 vote requirement.

The initial numbers are preregistered engineering defaults, not claims of
optimality. Any future tuning requires an explicit UPDATE-only research design
and must preserve validation/holdout boundaries.

## Data-source boundary

This change authorizes no new data source. In particular it does not authorize:

- fetching a proprietary TOTAL3 series;
- fetching historical BTC dominance;
- provider mixing without lineage;
- new R2 namespaces or writes;
- opening the replacement holdout;
- using current/future values to reconstruct historical context.

The existing Crypto Core 100 data can later support exchange-derived breadth
once its own scheduled materialization authority and completeness gates are
satisfied. Aggregate market-cap and dominance history still require their own
source/lineage decision.

## Trading boundary

The output is descriptive challenger evidence only. It does not alter:

- `config/strategy_v0_1.json`;
- strategy score or entry threshold;
- LONG-only/SHORT execution authority;
- risk per trade or leverage;
- paper/live order paths;
- model promotion;
- workflow schedules.

A future experiment may test whether these states improve out-of-sample
performance. Until that evidence exists, the correct interpretation is simply:
**market context observed, trading edge not established**.
