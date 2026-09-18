# Paper Loop Resume V0.1

Status date: 2026-09-18

Status: **PREPARED EXPLICIT-MANUAL-RESUME-ONLY / NO AUTOMATION / NO LIVE AUTHORITY**

## Purpose

Paper Loop Resume V0.1 is the explicit checkpoint-to-next-cycle boundary.

It consumes one verified Paper Loop Checkpoint and one explicit candidate basket,
then invokes the existing Paper Cycle Orchestrator with the checkpoint's exact
`next_account_input`.

The loop becomes:

```text
Paper Loop Checkpoint
        ↓
exact checkpoint-id confirmation
        ↓
checkpoint lineage + account/exposure validation
        ↓
existing Paper Cycle Orchestrator
        ↓
next paper cycle report
```

Resume V0.1 does not submit to PaperBroker, simulate lifecycle bars, write state
or schedule itself.

## Checkpoint validation

Before preparing the next cycle, Resume V0.1 recomputes and validates the
checkpoint.

The checkpoint itself binds:

- Account Advance id;
- Lifecycle Batch id;
- previous account snapshot id;
- next account snapshot id;
- SHA-256 of `next_account_input`;
- SHA-256 of current Portfolio existing exposure;
- SHA-256 of the exact Paper Account policy.

The carried Account policy matters because the next cycle must use the same
insolvency, mark-coherence and exposure-export rules that produced the
checkpoint.

## Exact confirmation

The caller must provide:

```text
confirmation_checkpoint_id == checkpoint_report.checkpoint_id
```

A generic yes/no flag is not accepted.

A stale or modified checkpoint report is rejected before the Paper Cycle engine
runs.

## Reuse of existing Cycle engine

Resume V0.1 does not implement:

- candidate ranking;
- Portfolio Admission;
- Position Sizing;
- Paper Execution intent creation.

It calls the existing `prepare_paper_cycle()` entrypoint with:

- checkpoint `next_account_input`;
- checkpoint Paper Account policy;
- explicit next-cycle candidate inputs;
- versioned Portfolio / Paper Execution / Cycle policies.

This keeps one canonical implementation of cycle preparation.

## Cross-cycle reconciliation

After the Cycle report is produced, Resume V0.1 verifies:

- Cycle `account_snapshot_id` equals Checkpoint `next_snapshot_id`;
- Cycle `existing_exposures` equals Checkpoint current exposure.

This prevents a next cycle from silently preparing against a different account
or portfolio book.

## Candidate causality and equity

All existing Paper Cycle gates remain active.

Therefore each candidate:

- must have `as_of_ms` at or after the checkpoint account timestamp;
- must use the checkpoint account equity in its Position Sizing plan;
- must pass the same Strategy Family Validation / Portfolio Admission rules.

A stale candidate sized from the previous cycle's equity fails closed.

## Valid next-cycle outcomes

Resume is successful even when the reused Cycle engine returns a valid
non-trading state such as:

- `NO_CANDIDATES`;
- `PORTFOLIO_REVIEW_REQUIRED`;
- `CYCLE_REVIEW_REQUIRED`.

A fully ready next cycle may return:

```text
PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION
```

Resume itself still performs zero broker submissions.

## Multi-cycle integrity audit

Paper Loop Integrity / Multi-Cycle Replay V0.1 can audit two or more completed
Resume-led rounds after the fact.

It recomputes Resume/Cycle/Session/Batch/Advance/Checkpoint ids, requires exact
Checkpoint payload chaining across rounds and verifies that deterministic replay
of the same transcript produces the same integrity id.

The Integrity layer is audit-only and does not execute Resume or any downstream
stage.

## CLI

```bash
PYTHONPATH=src python scripts/resume_paper_loop_v0_1.py \
  --input /tmp/paper-loop-resume-input.json \
  --confirm-checkpoint-id paper-loop-checkpoint-v0-1-...
```

Input shape:

```json
{
  "schema": "qookey-paper-loop-resume-input-v0.1",
  "checkpoint_report": {},
  "candidates": []
}
```

The CLI loads the existing Cycle, Portfolio Admission and Paper Execution
versioned policies. The exact Paper Account policy comes from the checkpoint.

## Explicit non-goals

V0.1 does not:

- query Binance, Pionex or MAX;
- access R2 or replacement holdout;
- persist checkpoint/account/broker state;
- schedule the next cycle;
- automatically generate candidates;
- submit paper orders;
- simulate fills;
- mutate strategy or risk rules;
- enable SHORT paper execution;
- create real-money orders;
- enable live trading.

## Authority

Paper Loop Resume V0.1 authorizes only one explicit manual checkpoint-to-cycle
preparation step.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic cycle, automatic/scheduled submission, SHORT paper execution, formal
trade-plan authority, real-money order authority or live-trading authority.
