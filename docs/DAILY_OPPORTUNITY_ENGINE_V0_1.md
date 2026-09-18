# Daily Opportunity Engine V0.1

Status date: 2026-09-18

## Role

Daily Opportunity Engine is the first product-stage selector in the Qookey Crypto Autopilot architecture.

It answers:

> Which assets deserve attention today?

It does **not** answer:

> Which order should be sent now?

V0.1 is deterministic, research-only and no-I/O. It consumes already-computed evidence and ranks multi-asset candidates.

## Inputs

- governed multi-asset universe candidates
- 24h quote turnover
- current spread
- closed-bar technical snapshots
- causally available market-regime context
- explicit `as_of_ms`

It performs no provider request, R2 read/write, holdout access, model inference, strategy routing, position sizing or order submission.

## V0.1 score

Maximum score: 100.

### Liquidity quality — 25

- turnover rank within the supplied governed universe: up to 15
- spread quality relative to the frozen maximum-spread bound: up to 10

### Directional structure — 75

The engine computes both a LONG_BIAS and SHORT_BIAS score. It does not hard-code the platform to long-only.

For each direction:

- coherent EMA20 / EMA50 / EMA200 stack: 20
- close on the directional side of EMA20: 10
- EMA20 slope/ATR directional agreement: 10
- MACD histogram directional agreement: 15
- RSI directional confirmation: 10
- Bollinger position directional confirmation: 5
- volume participation: 5

The larger directional score becomes the descriptive bias. A tie is `NEUTRAL`.

## Important boundary

The attention score is a transparent research heuristic. It is **not** evidence of statistical edge and it is not a trading recommendation.

A selected asset must still pass downstream:

1. Strategy Router
2. strategy-specific validation
3. risk / position sizing
4. paper execution
5. separately authorized live-trading gates

## Regime handling

V0.1 requires causal regime context by default so the downstream router receives the same point-in-time context.

Regime does not secretly add or subtract score in V0.1. This avoids mixing market-context classification with strategy compatibility before the Strategy Router exists.

## Zero-candidate behavior

The engine may return `NO_CANDIDATE`.

`maximum_candidates` is a ceiling only. It must never force the engine to produce a fixed number of daily assets or trades.

## Anti-leakage

- technical snapshots whose `available_at_ms` exceeds `as_of_ms` fail closed
- future regime snapshots fail closed
- missing full V0.2 technical warmup fails closed
- duplicate universe symbols are rejected
- no data repair, interpolation or future-bar lookup is performed

## V0.1 policy

Frozen research defaults:

- maximum candidates: 5
- minimum attention score: 65
- maximum spread: 30 bps
- minimum volume ratio confirmation: 1.0
- bullish RSI confirmation: >= 55
- bearish RSI confirmation: <= 45
- bullish Bollinger position confirmation: >= 0.55
- bearish Bollinger position confirmation: <= 0.45
- ready causal market regime required: true

These are product-research heuristics, not validated profitability thresholds. Future changes require a new version rather than silently rewriting V0.1.

## Next layer

After this selector is stable, Strategy Router V0.1 should consume:

- symbol
- opportunity score
- directional bias
- regime state
- technical evidence
- validated strategy-family registry

and return either a compatible strategy family or `NO_TRADE`.

## Authority

This component grants no:

- provider access
- R2 access
- holdout access
- source switch
- strategy promotion
- model promotion
- formal trade plan
- real-money order
- live trading
