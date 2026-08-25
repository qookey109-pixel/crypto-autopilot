# Paper LONG/SHORT Challenger V0.2

## Status

`PREPARED_LOCAL_REPLAY_ONLY`. This is a research challenger, not a replacement
for the governed `SState Intraday Wave V0.1` `LONG_ONLY` baseline.

## Purpose

V0.2 evaluates symmetrical directional hypotheses on closed candles:

- LONG: EMA/price trend, `+DI > -DI`, price above rolling VWAP and upper
  Donchian positioning.
- SHORT: inverse EMA/price trend, `-DI > +DI`, price below rolling VWAP and
  lower Donchian positioning.

The same causal indicators, fee model and slippage model are used for both
sides. RSI bands are side-specific to avoid treating a short setup as a blind
mirror of a long setup.

## Paper simulation boundary

- Maximum 12 independent samples per UTC day.
- Maximum 2 samples per symbol per UTC day.
- Reference risk is 0.25% equity per sample.
- Maximum leverage is 3x.
- Samples may overlap and are never presented as a composite portfolio curve.
- Long and short results are reported separately.
- Positive funding is a cost for LONG and a credit for SHORT in the research
  accounting model.
- No private API, R2 read/write, formal trade plan, automatic promotion or live
  order is authorized.

## Admission and promotion

The challenger must be evaluated independently with chronological walk-forward
folds, fees/slippage sensitivity, descriptive drawdown, side balance and regime
slices. A short sample or a good combined result cannot change V0.1. Promotion
would require a new versioned authority and an explicit review of long-only
baseline comparability, funding treatment, borrow/margin assumptions and
liquidation safeguards.

## Existing baseline

`config/strategy_v0_1.json`, `docs/STRATEGY_V0_1.md`,
`src/crypto_autopilot/backtest.py` and the Repository Paper Broker remain
unchanged. The challenger is isolated in
`src/crypto_autopilot/paper_long_short_challenger_v0_2.py`.
