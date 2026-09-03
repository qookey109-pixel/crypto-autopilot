# Failed Breakout Research V0.1

Status: **PREPARED / RESEARCH ONLY / NO STRATEGY AUTHORITY**

## Purpose

Add one causal market-structure research layer that distinguishes a breakout
which is accepted by subsequent closed bars from one that quickly falls back
through its reference level.

This work is motivated by the general market-structure question "did the market
accept the breakout or reject it?". It does **not** copy a commentator's fixed
BTC price levels into the strategy. No price such as 82,850, 76,000, 75,000, or
any other KOL level becomes a Repository strategy parameter.

## Existing foundation reused

V0.1 reuses `src/crypto_autopilot/features/structure.py`. That layer already
provides, on closed bars only:

- rolling previous high and low;
- close-above-range breakout and close-below-range breakdown flags;
- ATR-normalized distance to the previous range;
- delayed confirmed swing highs/lows;
- UP / DOWN / RANGE / INDETERMINATE market-structure state.

The existing structure engine is not rewritten.

## Candidate event

A research event begins only on the first closed-bar edge beyond the current
rolling range:

```text
inside / not-broken range
        ↓
first closed bar beyond previous range
        ↓
research breakout candidate
```

Consecutive bars that remain marked as breakout do not each create duplicate
candidates. Upside and downside events are labeled symmetrically for research,
but that symmetry does not authorize a SHORT strategy.

## Frozen initial resolution hypothesis

Initial V0.1 parameters are frozen in
`config/failed_breakout_research_v0_1.json`:

- follow-up window: 3 closed bars;
- accepted: 2 consecutive closes at least 5 bps beyond the reference level;
- failed: a close at least 5 bps back through the reference level;
- otherwise, after the complete 3-bar follow-up window: `EXPIRED`;
- insufficient future bars: `PENDING`.

These are preregistered research hypotheses, not profitability claims. They must
not be tuned using the replacement holdout.

## Causal availability

Every event records both:

- `breakout_available_at_ms`; and
- `resolved_at_ms` when an outcome becomes knowable.

Historical construction may know that an old breakout eventually failed, but
`breakout_events_as_of(...)` masks that future outcome back to `PENDING` for any
as-of timestamp before the resolution bar closed. This prevents the outcome
label from leaking backward into feature generation or model evaluation.

## Research outputs

The first useful evaluation should compare, on authorized non-holdout data:

1. acceptance rate;
2. failure rate;
3. bars to resolution;
4. forward returns conditional on ACCEPTED / FAILED / EXPIRED;
5. failure rate conditioned on existing market-structure/SState regimes;
6. later, only under separate authority, broader market-regime context such as
   BTC dominance or altcoin breadth.

A useful result would be evidence that the label adds stable predictive
information beyond the existing trend/setup features. A visually appealing
chart is not sufficient.

## Explicit non-authority

This stage does not:

- change `config/strategy_v0_1.json`;
- change the 80-point entry threshold;
- alter the current 4H -> 60M -> 15M Paper funnel;
- authorize SHORT entries;
- create paper/live orders;
- access a provider or R2;
- open the replacement holdout;
- promote a model;
- create a trade plan;
- authorize real-money or live trading.

A future strategy integration requires separate evidence, validation, and a
versioned strategy-authority change.
