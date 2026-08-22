# Pionex Public Paper Training Pipeline V0.1

## Flow

```text
GitHub Actions
  -> Pionex public futures market data
  -> causal technical and advanced market-state features
  -> bounded LONG candidate signals
  -> deterministic Repository Paper Broker replay
  -> run-scoped JSON artifact and forward-state cache
  -> read-only GitHub Pages projection
  -> Pionex Demo manual sampling only
```

Public calls are paced to three requests per second. The pipeline is a research and
execution-lifecycle rehearsal. It is not a profitability claim,
formal strategy promotion, provider substitution, private exchange integration or live-trading
authority.

## Feature families

- trend and momentum: EMA 20/50/200, RSI14, MACD, ADX14, +DI14 and -DI14;
- price/volume state: rolling VWAP, normalized VWAP distance, relative-volume z-score and
  Donchian position;
- volatility regime: ATR and Bollinger percentiles, realized and Parkinson volatility,
  volatility-of-volatility, Kaufman efficiency and Choppiness Index;
- derivative context: funding percentile, mark-index basis, basis z-score and open-interest
  snapshot/change when a prior forward observation exists;
- microstructure: taker trade imbalance/CVD, order-book imbalance, spread, depth and bounded
  expected buy slippage.

Only causal OHLCV features participate in the rolling replay. Current order-book, recent-trade,
funding/index and open-interest observations are attached as forward market-state evidence and are
never copied backward into historical candidate timestamps.

## Frozen candidate semantics

Candidate thresholds, ATR stop/target geometry, costs and risk limits are defined in
`config/paper_training_v0_1.json`. V0.1 is LONG-only, permits at most three new paper trades per UTC
day, risks 1% of current paper equity, caps required leverage at 3x, and uses explicit taker fees,
slippage and funding.

No parameter search, automatic promotion or automatic Pionex Demo interaction is authorized.

## V0.10 and holdout guard

At and after `2026-08-27T00:00:00Z`, the runner exits before constructing the Pionex client or
performing any provider request. This avoids contention with the frozen V0.10 capture window and
prevents the replacement holdout from entering a rolling candle request. Resumption requires a new
versioned authority after the existing scientific gates permit it.

## Storage

Each GitHub Actions run uploads the complete JSON report as a run-scoped artifact. A secret-free
cache carries only the latest public open-interest observations and up to 100 run summaries; cache
loss is acceptable and must never be repaired from private/provider-substituted data. GitHub Pages
shows the latest artifact projection with `authority=false` semantics.
