# Historical Liquidity -> Backtest Admission V0.1

## Purpose

Require each historical trade plan to pass both historical-market existence and point-in-time liquidity selection before it can be passed to Backtest Engine V0.1.

This closes a survivorship-bias path where a symbol may have valid historical candles but would not actually have belonged to the strategy's liquid-market candidate set at the signal timestamp.

## Admission chain

```text
LongTradePlan
  -> Historical Universe at plan.signal_time_ms
  -> Historical Liquidity batch available at plan.signal_time_ms
  -> complete-universe liquidity evidence gate
  -> point-in-time turnover/spread rank
  -> Historical Liquidity Admission
  -> Backtest Engine V0.1
```

The function never substitutes the current universe or the latest liquidity snapshot.

## Per-plan timestamp rule

Every plan is evaluated at its own `signal_time_ms`.

A plan from one historical timestamp and a plan from another historical timestamp may therefore use different liquidity batches and different rankings. Later rankings do not backproject into earlier signals.

## Evidence failure vs strategy rejection

V0.1 deliberately separates missing evidence from an ordinary strategy rejection.

The following conditions are evidence errors and abort admission rather than pretending the symbol simply failed the liquidity filter:

- no fresh point-in-time liquidity batch exists;
- the batch was not yet available at the signal timestamp;
- the batch is stale under the frozen policy;
- the complete evidence-bounded historical universe is not covered by the batch;
- native/proxy authority requirements are not satisfied.

This prevents missing data from silently changing the candidate set.

## Normal rejection reasons

When the required evidence exists, a plan can be rejected for two normal reasons:

- `symbol_not_historically_eligible_at_signal_time`
- `symbol_not_in_historical_liquidity_ranked_universe_at_signal_time`

A plan that passes receives:

- `historical_liquidity_eligible`

## Provenance

Each decision retains:

- plan id, symbol and signal timestamp;
- symbol-scoped Historical Universe authority references;
- liquidity batch id;
- liquidity source reference;
- optional liquidity source SHA-256;
- exact liquidity rank when admitted.

The liquidity source authority is preserved for rejected plans as well when a valid ranking batch existed, making the rejection replayable.

## Frozen policy source

The ranking policy is defined by `HistoricalLiquidityPolicy` and the machine-readable boundary `config/historical_liquidity_v0_1.json`.

V0.1 baseline:

- target size 15;
- maximum spread 30 bps;
- maximum snapshot age 24 hours;
- native-only;
- complete Historical Universe coverage required;
- rank by 24h quote turnover descending, spread ascending, symbol ascending.

## Current authority boundary

The code path is testable with deterministic fixtures, but real historical Pionex liquidity evidence has not yet been frozen PASS.

Therefore:

- `config/historical_liquidity_v0_1.json` remains `FRAMEWORK_ONLY`;
- this admission layer cannot yet authorize real historical plans;
- automatic historical trade-plan generation remains unauthorized;
- live trading remains forbidden.

## Regression coverage

Tests prove that:

- only point-in-time ranked symbols are admitted;
- each plan uses its own signal timestamp;
- a symbol outside Historical Universe is rejected even if it appears in the liquidity payload;
- stale/missing liquidity authority raises an evidence error;
- incomplete liquidity coverage raises instead of changing the candidate set;
- duplicate plan ids are rejected before admission;
- authority references and liquidity rank are retained.
