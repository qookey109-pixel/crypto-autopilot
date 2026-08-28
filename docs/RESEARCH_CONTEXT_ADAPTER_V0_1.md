# Research Context Adapter V0.1

Status: `PREPARED_NOT_ACTIVE`.

This adapter adds a bounded research vocabulary inspired by the supplied
technical-radar, multi-timeframe, bull/bear and Bitcoin-cycle references:

- `features/advanced.py` now exposes causal Stoch RSI, Williams %R, CCI,
  Awesome Oscillator, Ultimate Oscillator, Hull MA distance and Ichimoku base
  distance features.
- `training/shadow_ablation.py` evaluates them as isolated `oscillators`,
  `trend_structure` and `extended_technical` Challenger groups.
- `research/context.py` stores timestamped source observations without turning
  them into a composite buy/sell score.  It rejects future timestamps, invalid
  HTTPS lineage, non-finite values and unavailable observations containing
  fabricated numbers.

The source catalog is recorded in
`config/research_context_v0_1.json`.  It is a declaration, not a network
fetcher or a schedule.  A future authorized ingestion path must require
structured source evidence, retain the source URL and freshness status, and
keep daily/weekly/monthly horizons separate from the existing Pionex and
Binance provider paths.

This layer remains research-only: it cannot trigger a trade, create a trade
plan, promote a model or enable live trading.  Activation requires a separate
post-window versioned authority and the existing walk-forward, calibration,
cost, drawdown and exposure gates.
