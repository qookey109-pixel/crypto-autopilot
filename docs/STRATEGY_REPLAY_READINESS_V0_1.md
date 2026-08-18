# Strategy Replay Readiness V0.1

## Purpose

Strategy Replay Readiness V0.1 prevents the historical research pipeline from silently inventing missing strategy semantics.

The project already has raw historical/technical/SState/backtest boundaries, but the strategy authority does **not** yet freeze every rule needed to create a complete historical trade plan. This gate makes that incompleteness machine-visible.

## Frozen rules currently evaluable

From `docs/STRATEGY_V0_1.md` and `config/strategy_v0_1.json`, the following can be evaluated without interpretation:

### SState background gate

- state is one of `S3`, `S0.5`, `S2`, `S1`,
- probability is available,
- samples >= 50,
- probability >= 0.60.

The probability remains a background gate only and is not relabeled as an intraday trade win probability.

### 1H setup baseline

- EMA20 > EMA50,
- EMA20 slope > 0,
- close > EMA20.

If technical warmup is incomplete, these gates fail closed.

## Explicitly UNDEFINED rules

The current authority names but does not fully define:

- ATR-normalized overextension threshold,
- exact pullback-toward-EMA20 semantics,
- exact EMA20 reclaim semantics,
- exact previous-high break semantics,
- volume confirmation multiplier/threshold,
- exact ATR buffer size for structural stop placement.

These are returned as `UNDEFINED`, not guessed.

## Authorization rule

`ReplayReadiness.trade_plan_authorized` remains `False` while mandatory strategy semantics are undefined.

This is intentional. Backtest Engine V0.1 can simulate an explicitly supplied `LongTradePlan`, but the project is **not yet authorized to auto-generate those plans from historical candles/SState** until the undefined rules are versioned and validated.

## Why FAIL and UNDEFINED are different

- `FAIL` means an existing frozen rule was evaluated and did not pass (for example EMA20 <= EMA50).
- `UNDEFINED` means the project has not yet frozen enough semantics to evaluate the rule at all.

This distinction prevents parameter absence from being confused with a market-condition rejection.

## Next evidence step

The undefined rules should be introduced through a separate versioned parameter-freeze / sweep process. Candidate values must be tested for stability across independent data rather than selected only because they maximize one backtest sample.

Until that evidence exists, no automatic end-to-end historical strategy replay may be labeled authoritative.

## Safety

This gate:

- does not modify SState core,
- does not invent missing strategy thresholds,
- does not authorize live trading,
- does not submit orders,
- does not weaken existing deterministic risk gates,
- remains research/backtest infrastructure only.
