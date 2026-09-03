# Contextual Edge Evaluation V0.1

Status: **PREPARED RESEARCH-ONLY / NO STRATEGY AUTHORITY**

## Purpose

This layer answers one narrow question:

> Do Failed Breakout Research V0.1 outcomes behave differently across the
> causally available Market Regime / Altcoin Breadth V0.1 states?

It does not add a trading signal. It produces descriptive research evidence so
future work can decide whether a regime interaction deserves a separately
versioned candidate and formal validation.

## Position in the research stack

```text
closed candles
  -> market structure
  -> Failed Breakout Research V0.1

closed cross-market context
  -> Market Regime / Altcoin Breadth V0.1

breakout event + regime known at that event
  -> Contextual Edge Evaluation V0.1
  -> descriptive slices only
  -> future candidate design, if justified
  -> Strategy Edge Validation V0.1
  -> human review only
```

The formal Paper strategy remains unchanged.

## Causal join rule

For every breakout event, V0.1 selects exactly the latest regime snapshot whose
availability timestamp satisfies:

```text
regime.available_at_ms <= breakout.breakout_available_at_ms
```

A regime that becomes available one millisecond after the breakout is not
eligible for that breakout.

This rule matters because the breakout result may resolve several bars later.
The later regime must not be attached retroactively to the earlier event.

Events that occur before the first available regime are retained as unmatched
audit evidence instead of being dropped or backfilled.

## Historical as-of rule

When an `as_of_ms` boundary is supplied, the evaluator reuses the Failed
Breakout layer's causal projection. A historically `ACCEPTED`, `FAILED`, or
`EXPIRED` event is projected back to `PENDING` when its resolution was not yet
known at that as-of timestamp.

Thus the report can be reconstructed without leaking a future resolution into
an earlier research view.

## Slice dimensions

V0.1 preregisters only two dimensions:

- breakout direction (`UP` / `DOWN`);
- regime state.

Current regime states can include:

- `ALT_EXPANSION`;
- `BTC_CONCENTRATION`;
- `BROAD_RISK_OFF`;
- `MIXED`;
- `INSUFFICIENT`.

No extra level, coin, creator, KOL, calendar window, or hand-picked market
condition may be added post hoc and presented as the same V0.1 experiment.

## Reported metrics

For each direction baseline and each direction/regime slice, V0.1 records:

- total events;
- resolved events;
- decisive events (`ACCEPTED + FAILED`);
- accepted events;
- failed events;
- expired events;
- pending events;
- resolution rate;
- decisive acceptance rate;
- expiry rate among resolved events.

For eligible slices, it additionally reports:

```text
decisive_acceptance_uplift_vs_direction
  = slice decisive acceptance rate
  - same-direction baseline decisive acceptance rate
```

The comparison is direction-matched. An upside-breakout slice is never compared
with a mixed UP/DOWN baseline.

## Minimum sample rule

The preregistered minimum is **30 decisive events** in both:

1. the direction/regime slice; and
2. the same-direction baseline.

Before both requirements are satisfied, uplift remains `null` and
`comparison_eligible=false`.

`INSUFFICIENT` regime slices are always ineligible for uplift even when they
contain many events. They remain visible only for auditability.

The number 30 is a reporting floor, not a statistical-significance threshold.
It does not prove an edge.

## What V0.1 deliberately does not claim

A positive uplift is not:

- a profitable strategy;
- a statistically significant discovery;
- a permission to modify the 80-point Paper score;
- a permission to skip the existing SState / trend / entry gates;
- a SHORT authorization;
- a model-promotion gate;
- evidence that a regime causes a breakout outcome;
- protection against data snooping or multiple testing.

Formal statistical anti-overfitting work belongs to the already prepared
`Strategy Edge Validation V0.1` layer. Contextual Edge Evaluation V0.1 does not
reimplement or bypass that layer.

## Data-source boundary

This module contains no provider fetcher and no production-storage path.

The Market Regime layer still requires separately authorized source lineage for
aggregate ex-BTC/ETH market capitalization and BTC dominance history. Crypto
Core 100 may later provide exchange-derived breadth only under its own complete
materialization authority.

The frozen replacement holdout is not an input to V0.1 and must remain unopened.

## Authority boundary

All of the following remain false:

- provider access;
- production R2 read/write;
- replacement holdout access or tuning;
- scheduled workflow execution;
- strategy-parameter changes;
- strategy-score changes;
- SHORT execution;
- automatic model promotion;
- trade-plan authority;
- real-money orders;
- live trading.

## Next valid use

After a sufficiently large, causally aligned non-holdout dataset exists, this
report may identify descriptive interactions worth preregistering as new
candidate hypotheses. Any such candidate must be versioned separately and pass
the normal causal replay, cost/risk checks, disjoint validation, Strategy Edge
Validation V0.1, and human review before it can affect any formal strategy.
