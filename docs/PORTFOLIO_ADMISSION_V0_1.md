# Portfolio Admission V0.1

Status date: 2026-09-18

Status: **PREPARED RESEARCH/PAPER-ONLY / NO LIVE AUTHORITY**

## Purpose

Portfolio Admission V0.1 adds the missing basket-level risk gate between
single-route position sizing and Paper Execution.

The product flow is now:

```text
Daily Opportunity Engine
        ↓
Strategy Router
        ↓
Strategy Family Validation
        ↓
Risk / Position Sizing
        ↓
Portfolio Admission
        ↓
Paper Execution
        ↓
Repository Paper Broker
        ↓
Paper Fill / Order Lifecycle
        ↓
Paper Account / Position State
        ↺ existing exposure into next Portfolio Admission
```

A sizing plan that is safe in isolation is not automatically safe in a
portfolio.

## V0.1 is an admission gate, not an optimizer

V0.1 evaluates one explicit proposed basket.

It deliberately does **not**:

- rank strategy families;
- select a winner;
- automatically choose a subset when the full basket breaches a limit;
- invent a strategy score;
- optimize expected return.

If the explicit basket violates a frozen limit, V0.1 returns
`PORTFOLIO_REVIEW_REQUIRED` and admits none of the new proposals.

This avoids disguising an arbitrary tie-break as a portfolio optimizer.

## Proposal lineage

Every new proposal binds:

- symbol;
- registered strategy family;
- governed overlap group;
- direction;
- as-of timestamp;
- complete Strategy Family Validation report SHA-256;
- sizing equity basis;
- entry price;
- stop price;
- approved notional;
- realized risk;
- target risk;
- risk utilization.

The deterministic proposal id is SHA-256-derived.

Changing the family evidence or any material sizing geometry therefore produces
a different proposal id.

All new proposals in one basket must use the same equity basis as the portfolio
evaluation.

## Existing exposure

V0.1 may receive existing open research/paper exposures.

Existing exposure is counted before new proposals for:

- total realized risk;
- symbol realized risk;
- gross notional;
- symbol notional;
- strategy-overlap risk;
- routes per symbol;
- direction conflicts.

The gate therefore cannot evaluate a new order as though the current book were
empty.

Paper Account / Position State V0.1 now provides the canonical product-stage
source for current paper exposure. Its export uses current mark notional and the
current mark-to-stop nominal loss for each open LONG position.

An insolvent paper account cannot export new Portfolio Admission capacity.

## Frozen V0.1 limits

Default policy:

| Gate | Limit |
| --- | ---: |
| total realized risk | 3% of equity |
| realized risk per symbol | 1.5% of equity |
| realized risk per strategy-overlap group | 2% of equity |
| gross notional | 3.0x equity |
| notional per symbol | 1.5x equity |
| routes per symbol | 2 |
| opposing LONG/SHORT on same symbol | not allowed |
| automatic subset selection | not authorized |

These are conservative product defaults for research/paper admission. They are
not claims of optimal portfolio construction.

## Why Risk can pass while Portfolio rejects

Risk / Position Sizing V0.1 evaluates a single route.

For example, a 100 USD account with a very tight valid stop may produce:

- target risk: 1 USD;
- approved notional after the 3x leverage cap: 300 USD;
- realized risk: 0.60 USD.

The single-route risk plan is valid.

However, Portfolio V0.1 has a 1.5x per-symbol notional cap. A 300 USD BTC
proposal on 100 USD equity is therefore rejected at the portfolio layer.

This is intentional:

> risk-safe in isolation does not imply concentration-safe in the portfolio.

Portfolio does not alter the stop or resize the position in V0.1. It simply
refuses the proposed basket.

## Strategy-overlap groups

V0.1 uses explicit overlap buckets as a conservative correlation proxy.

### DIRECTIONAL

- TREND_FOLLOWING
- BREAKOUT
- MOMENTUM
- HIGH_VOLATILITY_TREND

### RANGE

- MEAN_REVERSION
- LOW_VOLATILITY_RANGE

The overlap registry must cover the complete Multi-Strategy Library. If a new
strategy family is added without a governed overlap group, validation fails
closed.

This is not a statistical correlation model. A later version may consume
point-in-time covariance/correlation evidence under a separate contract.

## Outcomes

### PORTFOLIO_ADMITTED

Every frozen basket-level gate passes.

All proposal ids in the explicit basket are listed in
`admitted_proposal_ids`.

### PORTFOLIO_REVIEW_REQUIRED

One or more limits are violated.

V0.1 admits none of the new proposals because automatic subset optimization is
not authorized.

### NO_PROPOSALS

The explicit proposal set is empty.

## Paper Execution dependency

Paper Execution V0.1 now requires a complete
`qookey-portfolio-admission-report-v0.1`.

Paper Execution:

1. reconstructs its exact portfolio proposal from family evidence and sizing;
2. verifies the portfolio report state is `PORTFOLIO_ADMITTED`;
3. verifies the exact proposal id appears in `admitted_proposal_ids`;
4. verifies portfolio authority remains closed;
5. SHA-256 binds the full portfolio report into the paper intent.

A single sizing plan can no longer bypass portfolio-level exposure checks.

## CLI

Portfolio admission can be evaluated without network or broker access:

```bash
PYTHONPATH=src python scripts/admit_portfolio_v0_1.py \
  --input /tmp/portfolio-input.json
```

The input contains:

- portfolio equity;
- zero or more existing exposures;
- one or more proposed routes;
- complete family-validation reports;
- complete Position Sizing V0.1 plans.

The CLI reconstructs governed proposal ids rather than trusting caller-supplied
ids.

## Current limitations

V0.1 does not model:

- measured return correlation;
- covariance matrices;
- beta or factor exposure;
- liquidation coupling;
- cross-margin effects;
- expected-return optimization;
- Kelly allocation;
- dynamic subset optimization;
- strategy ranking.

Those require separately validated evidence and should not be inferred from
family names.

## Authority

Portfolio Admission V0.1 grants no provider access, R2 access, replacement
holdout access, source switch, strategy ranking, automatic subset selection,
strategy/model promotion, PaperBroker submission, SHORT paper execution,
formal trade plan, real-money order or live-trading authority.
