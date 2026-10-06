# Prospective Shadow Collection Runtime V0.1

Status date: 2026-10-06

Status: **IMPLEMENTED FOR AUTHORIZED MAIN-ONLY RESEARCH COLLECTION**

## Scope

This implementation is bound to the execution authority merged by PR #772.

The workflow runs on the protected default branch only and is eligible for:

- natural schedule: minute 17 every four hours;
- manual workflow_dispatch.

The runtime hard-stops outside the bounded 90-day window ending
2027-01-04T08:00:00Z.

## Per-run network budget

Exactly 10 public no-key requests are expected on a successful run:

- Pionex: 8
  - live perpetual symbols: 1
  - perpetual tickers: 1
  - perpetual book tickers: 1
  - 60M candles for the top five governed research markets: 5
- CoinPaprika: 2
  - global market snapshot: 1
  - ETH ticker snapshot: 1

There are no automatic retries or fallback providers.

## Governed universe

The collector reuses the existing Pionex Research Universe V0.1 selector.

The selector preserves the established semantics:

- liquidity-ranked crypto core target;
- explicit meme candidate watchlist;
- provider-native tokenized alternative-asset registry;
- minimum 150 selected research markets when provider evidence supports it.

Only the top five governed markets receive the bounded 60M candle capture in
this collector.

## Stored artifact evidence

The artifact contains normalized secret-free evidence only:

- normalized CoinPaprika TOTAL3 / BTC-dominance context and raw-payload hashes;
- top-five governed market metadata;
- 240 closed 60M candles for each of the five markets;
- deterministic technical indicators;
- market structure;
- deterministic liquidity/FVG/order-block/harmonic/MACD pattern evidence;
- volume-based Market Event Radar evidence;
- a research-only top-five breadth proxy;
- immutable record SHA-256.

Raw provider response bytes are not persisted.

## Replay boundary

The collector intentionally does not choose a signal or evaluate a future
outcome during the same run.

This prevents collection code from silently changing Daily Opportunity Engine
V0.1 or Strategy Router V0.1.

After enough prospective artifacts exist, a separately reviewed replay stage
can reconstruct causal decisions using only evidence whose artifact timestamp
was available at that historical decision time.

The top-five breadth field is explicitly labeled a research proxy and does not
claim production Market Regime equivalence.

## Persistence

The only durable runtime output is a GitHub Actions Artifact retained for 90
days.

No R2, D1 or repository runtime write is used.

## Safety

The runtime does not access:

- holdout data;
- training;
- model promotion;
- private exchange/account APIs;
- Paper order submission;
- real-money orders;
- live trading.
