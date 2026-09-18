# Paper Cycle Orchestrator V0.1

Status date: 2026-09-18

Status: **PREPARED MANUAL-CYCLE-ONLY / NO AUTOMATIC SUBMISSION**

## Purpose

Paper Cycle Orchestrator V0.1 gives the product one deterministic entrypoint for
preparing the next explicit paper cycle from the current paper account state.

The V0.1 path is:

```text
Paper Account / Position State
        ↓
current equity + existing open exposure
        ↓
explicit candidate basket
        ↓
Portfolio Admission
        ↓
Paper Execution decisions
        ↓
paper intents ready for explicit submission
```

It deliberately stops **before** Repository Paper Broker submission.

This stage does not schedule itself, submit orders, simulate fills, advance
lifecycle state or write persistent account state.

## Why this stage exists

Before V0.1, each product component could be called independently.

That was useful for testing but left one integration risk: a caller could
accidentally use stale equity, forget existing open exposure or prepare paper
execution from a portfolio view that did not match the current Paper Account.

Paper Cycle V0.1 makes the current Paper Account snapshot the canonical source
for:

- account equity;
- account timestamp;
- current existing exposure.

The same account snapshot is then used for all candidate admission in that
cycle.

## Candidate input

Each explicit candidate supplies:

- symbol;
- registered strategy family;
- decision timestamp;
- complete Strategy Family Validation report;
- complete Risk / Position Sizing V0.1 plan.

The cycle does not generate candidates and does not rank them.

Candidate generation still belongs upstream to Daily Opportunity + Strategy
Router.

## Frozen V0.1 cycle rules

- maximum candidates: 5;
- candidate timestamp must be at or after current account snapshot;
- complete admitted basket must be paper-intent-ready;
- candidate order is canonicalized by deterministic portfolio proposal id;
- no subset optimization;
- no strategy ranking;
- no partial-basket submission;
- no automatic Paper Broker submission;
- no lifecycle simulation;
- no persistent state write.

If one admitted candidate cannot produce a valid Paper Execution decision, the
entire cycle becomes `CYCLE_REVIEW_REQUIRED`.

V0.1 does not silently keep only the candidates that happened to pass.

## Account-first semantics

The orchestrator first rebuilds Paper Account / Position State V0.1.

If the account is not active:

```text
ACCOUNT_BLOCKED
```

No portfolio or paper intent is prepared.

If active, current open positions are exported into Portfolio Admission as
existing exposure.

New sizing plans must use the same equity basis as the materialized account.

## Portfolio outcomes

### NO_CANDIDATES

The explicit candidate set is empty.

No trade is forced.

### PORTFOLIO_REVIEW_REQUIRED

The complete proposed basket breaches one or more Portfolio Admission V0.1
limits.

No Paper Execution decision is prepared.

### PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION

The account is active, the complete basket is admitted and every candidate
produces `READY_FOR_PAPER_BROKER`.

The report includes the full Paper Execution decisions and deterministic intent
ids.

**No broker submission has occurred.**

### CYCLE_REVIEW_REQUIRED

Portfolio admission passed, but one or more candidates cannot become a valid
paper intent, for example because SHORT paper execution remains unauthorized.

The entire basket remains blocked from explicit submission.

## Deterministic cycle id

The cycle id binds:

- Paper Account snapshot id;
- cycle state;
- canonical Portfolio Admission report SHA-256;
- proposal ids;
- Paper Execution decision status/reason;
- intent ids where present.

Candidate input ordering does not change the cycle id.

## Explicit submission boundary

Paper Cycle V0.1 reports:

```text
broker_submissions_performed = 0
explicit_submission_required = true
```

Only a fully ready cycle reports:

```text
explicit_submission_allowed = true
```

The actual `submit_paper_execution()` call remains a separate explicit action.

This preserves the existing project rule that paper execution preparation does
not silently become unattended execution.

## CLI

A no-network CLI is provided:

```bash
PYTHONPATH=src python scripts/prepare_paper_cycle_v0_1.py \
  --input /tmp/paper-cycle-input.json
```

Input shape:

```json
{
  "schema": "qookey-paper-cycle-input-v0.1",
  "account_input": {
    "schema": "qookey-paper-account-state-input-v0.1",
    "initial_equity_usd": 100.0,
    "records": [],
    "marks": []
  },
  "candidates": []
}
```

The CLI loads the versioned account, portfolio, paper-execution and cycle
policies.

Valid non-trading outcomes such as `NO_CANDIDATES` or
`PORTFOLIO_REVIEW_REQUIRED` are valid cycle reports, not CLI failures.

## What V0.1 does not do

V0.1 does not:

- query Binance, Pionex or MAX;
- read or write R2;
- access replacement holdout;
- rank strategy families;
- optimize a portfolio subset;
- submit to PaperBroker;
- simulate fills;
- advance lifecycle state;
- persist account state;
- schedule recurring cycles;
- enable SHORT paper execution;
- create formal trade plans;
- place real-money orders;
- enable live trading.

## Downstream explicit submission

Paper Submission Session V0.1 is now the separate downstream boundary.

It requires exact cycle-id confirmation, recomputes the cycle id from report
contents, preflights the complete admitted basket and submits only to the
existing in-memory Repository Paper Broker.

It still grants no unattended scheduling, persistent broker state or real-money
execution authority.

## Authority

Paper Cycle Orchestrator V0.1 grants manual deterministic cycle preparation
only.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic/scheduled Paper Broker submission, lifecycle execution, SHORT paper
execution, formal trade-plan authority, real-money order authority or
live-trading authority.
