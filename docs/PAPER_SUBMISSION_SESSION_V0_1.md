# Explicit Paper Submission / Session Coordination V0.1

Status date: 2026-09-18

Status: **PREPARED EXPLICIT-PAPER-SUBMISSION-ONLY / NO AUTOMATION / NO LIVE AUTHORITY**

## Purpose

Paper Submission Session V0.1 is the explicit authority boundary between a
fully-ready Paper Cycle and the existing in-memory Repository Paper Broker.

The product path is:

```text
Paper Cycle Orchestrator
        ↓
PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION
        ↓
exact cycle-id confirmation
        ↓
complete-basket preflight
        ↓
Repository Paper Broker submissions
        ↓
Paper Execution evidence
        ↓
Paper Fill / Order Lifecycle
```

The session is not a scheduler and does not run lifecycle simulation.

## Exact confirmation

V0.1 does not accept a generic yes/no flag.

The caller must provide the exact deterministic cycle id:

```text
confirmation_cycle_id == cycle_report.cycle_id
```

The cycle id is recomputed from the report before any broker mutation. A
modified cycle report with a stale id is rejected.

## Complete-basket semantics

The session accepts only:

```text
PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION
```

and requires:

- `explicit_submission_required = true`;
- `explicit_submission_allowed = true`;
- zero previous broker submissions in the cycle report;
- zero lifecycle simulations;
- zero persistent state writes;
- a `PORTFOLIO_ADMITTED` basket;
- every admitted proposal represented exactly once;
- every Paper Execution decision ready;
- every prepared-intent row matching its decision.

V0.1 does not submit only the convenient subset.

## Preflight before mutation

All intents are validated before the first new PaperBroker order is appended.

Existing broker orders are allowed only when:

- the same order id exists;
- symbol matches;
- side matches;
- notional matches exactly.

Any mismatch is an idempotency collision and rejects the session before new
orders are created.

The underlying PaperBroker now independently enforces the same collision rule.

## Idempotent replay

Replaying the same session against the same in-memory broker is valid.

Matching existing orders return:

```text
replayed = true
```

The deterministic session id remains unchanged.

A partially replayed broker may contain some exact matching orders; the session
preflights the complete basket, reuses exact matches and submits only the
missing intents.

## Output

A successful report contains:

- deterministic session id;
- cycle id;
- intent count;
- new submission count;
- replayed submission count;
- broker order count after submission;
- per-proposal Paper Execution receipts;
- complete Paper Execution evidence for downstream Lifecycle use.

The session does not generate fills.

## Downstream lifecycle batch

Paper Lifecycle Batch Coordination V0.1 now consumes the accepted Session
report.

It requires exact session-id confirmation and one lifecycle input per accepted
proposal, then reuses Paper Fill / Order Lifecycle V0.1 for the complete basket.

The Session stage itself still performs zero lifecycle simulations.

## CLI

```bash
PYTHONPATH=src python scripts/submit_paper_session_v0_1.py \
  --cycle-report /tmp/paper-cycle-report.json \
  --confirm-cycle-id paper-cycle-v0-1-...
```

The CLI creates a new in-memory Repository Paper Broker for that invocation.

It does not persist broker state. Replaying across separate CLI processes
therefore requires a future separately governed persistence/session-state layer.

## Deliberate limitations

V0.1 does not:

- query Binance, Pionex or MAX;
- access R2 or replacement holdout;
- schedule submissions;
- automatically submit future cycles;
- persist PaperBroker state;
- simulate fills;
- advance lifecycle state;
- enable SHORT paper execution;
- create real exchange orders;
- enable live trading.

## Authority

Paper Submission Session V0.1 authorizes only an explicit invocation to the
existing **in-memory paper-only broker**, after exact cycle-id confirmation and
complete-basket preflight.

It grants no provider access, R2 access, holdout access, persistent broker
state, automatic/scheduled submission, lifecycle simulation, SHORT paper
execution, formal trade-plan authority, real-money order authority or
live-trading authority.
