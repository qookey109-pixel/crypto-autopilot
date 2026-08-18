# Historical Universe → Backtest Admission V0.1

## Purpose

Make historical-universe authority an explicit prerequisite before any `LongTradePlan` is handed to the Backtest Engine.

This closes a survivorship-bias gap: a market that exists today must not be silently treated as if it existed, or had complete native data, at an earlier backtest timestamp.

## Admission rule

Every plan is evaluated at its own `signal_time_ms`.

V0.1 requires native evidence for all three baseline intervals at that timestamp:

- `15M`
- `60M`
- `4H`

The gate calls the existing `HistoricalUniverseIndex` with `native_only=True`.

A plan is admitted only when its symbol is in the evidence-bounded historical snapshot for that exact signal time.

## No current-universe fallback

The gate never substitutes:

- today's active Pionex markets;
- the latest snapshot;
- a later verified partition;
- a proxy/external-provider observation.

Later evidence therefore cannot retroactively authorize an earlier trade plan.

## Provenance

For an admitted plan, the decision records the source references that support the plan symbol's required interval coverage at the signal timestamp.

Authority references are scoped to the plan symbol rather than copying unrelated market references from the whole snapshot.

A symbol reported eligible without any supporting authority reference is treated as an internal safety error rather than being silently admitted.

## Rejection

Current V0.1 rejection reason:

`symbol_not_historically_eligible_at_signal_time`

Rejected plans are returned separately and are not passed to the Backtest Engine.

## Determinism and identity

- input order is preserved;
- every plan is checked independently at its own timestamp;
- duplicate `plan_id` values are rejected before admission;
- repeated evaluation with the same index and plans returns the same admission result.

## Relationship to other layers

```text
Historical partition receipts / listing authority
        ↓
HistoricalUniverseIndex
        ↓
Historical Universe → Backtest Admission V0.1
        ↓ admitted plans only
Backtest Engine V0.1
```

For automatic historical strategy replay, this admission gate is still downstream of:

```text
Technical Features
Historical SState evidence + replay
Strategy Replay Readiness
Validated/frozen strategy parameters
```

Those upstream gates remain independent and cannot be bypassed merely because a symbol passes historical-universe admission.

## What this does not prove

This layer does not create missing historical market evidence. It only enforces evidence already represented by `HistoricalUniverseIndex`.

Therefore:

- the one-year Historical Backfill Pilot still needs a real PASS authority receipt;
- full 8-year historical universe reconstruction remains incomplete;
- historical liquidity ranking remains incomplete;
- automatic trade-plan generation remains unauthorized;
- `trade_plan_authorized` remains false.

## Safety

- Native-only V0.1 admission.
- No proxy data is relabeled as Pionex-native.
- No SState core modification.
- No private Pionex API.
- No live orders.
- Research/backtest-only.
