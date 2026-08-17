# SState Intraday Wave V0.1

## Purpose

Create a falsifiable baseline for an intraday crypto perpetual strategy. Every parameter in this document is a starting hypothesis, not a profitability claim.

## Market funnel

```text
Pionex PERP universe
  -> liquidity/data-quality gate
  -> approximately 15 active markets
  -> 4H SState gate
  -> 1H trend/setup gate
  -> 15m entry gate
  -> opportunity score
  -> risk engine
  -> paper order
```

## 4H market context

Allowed SState values:

1. S3
2. S0.5
3. S2
4. S1

S0 and OTHER are skipped in V0.1.

Historical probability is a background gate only. Current SState probability horizons were designed for a different horizon; V0.1 must not label that value as the intraday trade win probability.

Initial probability gate:

- available = true
- samples >= 50
- probability >= 60%

Planned sweeps: 55%, 60%, 65%, 70%.

## 1H setup

Initial feature gate:

- EMA20 > EMA50
- EMA20 slope > 0
- close > EMA20
- avoid excessive extension from EMA20 (ATR-normalized)

## 15m entry

Target pattern: pullback -> reclaim -> continuation.

Initial features:

- pullback toward EMA20
- reclaim EMA20
- break previous candle high
- volume confirmation

## Opportunity score

100-point provisional model:

- SState quality: 25
- historical probability: 20
- 1H trend: 20
- 15m entry: 20
- reward/risk: 10
- liquidity/funding: 5

Minimum entry score: 80.

Weights are provisional and must be tested for stability; do not tune them only to maximize one backtest sample.

## Risk

- 1R = 1% equity by default
- maximum 3 new trades/day
- maximum leverage = 3x
- isolated-margin design target
- daily new-entry shutdown at -3R

Position notional:

```text
risk_usd = equity * risk_fraction
notional = risk_usd / stop_distance_fraction
required_leverage = notional / equity
```

If required leverage exceeds the configured maximum, skip the trade instead of widening the risk budget.

## Stop

Use a structural 15m swing invalidation plus a small ATR buffer. A fixed percentage stop across all assets is not the baseline.

## Exit

Initial research model:

- at +1R: realize 30%
- remaining 70% becomes a runner controlled by a trailing/invalidation rule
- maximum holding target: 12h

## V0.1 prohibited behavior

- live orders
- forced daily trade quota
- >3x leverage
- martingale/loss doubling
- unlimited averaging down
- liquidation as stop-loss
- direct SHORT mirroring before independent validation
- LLM bypass of deterministic risk gates
