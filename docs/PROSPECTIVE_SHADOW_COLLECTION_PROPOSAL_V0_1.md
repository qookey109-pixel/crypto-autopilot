# Prospective Shadow Collection Proposal V0.1

Status date: 2026-10-06

Status: **PREPARED NOT ACTIVE**

## Why this document exists

PRs #768 through #770 implement the research-only sensing, deterministic
technical translation, frozen shadow records and aggregate analysis requested
by the 2026-10-06 integration report.

The remaining evidence cannot be manufactured immediately: a true prospective
comparison needs new observations collected after the signal timestamp for
roughly 30 to 90 days.

This proposal defines that future collection boundary without turning it on.

## Proposed cadence

The proposed design is:

- create a new signal snapshot only on each closed 4H decision boundary;
- use an hourly settlement pass to fill +1h / +4h / +12h / +24h outcomes when
  their exact horizon becomes available;
- keep the existing Daily Opportunity Engine V0.1 maximum of five candidates
  as a ceiling, never a target number of trades;
- preserve NO_CANDIDATE and NO_TRADE as valid outcomes.

This cadence is only a proposal. No workflow or cron is added by this version.

## Source boundary

A future collector should reuse a governed causal public-market source instead
of inventing another authority path.

Market Event Radar and Technical Confluence remain research sidecars. They
cannot modify Opportunity V0.1 or Strategy Router V0.1 during the collection
period.

Clef / Clef-flash remains offline-only until a separate provider authority is
reviewed.

Yaozi comparison data is a separate limitation: the project does not have a
governed private Yaozi API or exact backend scoring feed. Therefore V0.1 cannot
pretend to automatically capture Yaozi. Any comparison record must be
prefetched/manual evidence with provenance until a governed source exists.

## Persistence blocker

A real 30-90 day test needs durable evidence. This proposal deliberately does
not choose one silently.

Still closed:

- R2 writes;
- D1 writes;
- GitHub artifact persistence;
- repository-commit persistence.

The future authority must choose one backend, define retention and cost limits,
and prove that the chosen route does not violate the project's zero-cost and
writer-governance constraints.

## Exact activation blockers

Before collection can start:

1. select and authorize the causal public-market collection path;
2. select the evidence backend and retention policy;
3. set finite request/storage budgets;
4. define comparison-signal provenance;
5. merge a separate finite execution authority;
6. only then add or enable a workflow schedule.

## What is already ready

The code needed after observations exist is already present:

- Market Event Radar V0.1;
- Technical Confluence Sidecar V0.1;
- deterministic liquidity/FVG/order-block/harmonic/MACD detectors;
- frozen signal and outcome IDs;
- +1h/+4h/+12h/+24h evaluation;
- MFE / MAE;
- signal latency;
- NO_TRADE quality;
- directional expectancy aggregation;
- 30-90 day collection maturity labels.

## Authority

This proposal authorizes nothing operational. It creates no workflow, makes no
network request, writes no persistent evidence, and changes no trading gate.
