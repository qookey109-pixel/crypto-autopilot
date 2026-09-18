# Paper Loop Checkpoint V0.1

Status date: 2026-09-18

Status: **PREPARED PORTABLE-HANDOFF-ONLY / NO PERSISTENCE / NO LIVE AUTHORITY**

## Purpose

Paper Loop Checkpoint V0.1 creates one deterministic, portable handoff after a
successful Paper Account Advance.

It carries the exact `next_account_input` needed by the next manual Paper Cycle
and binds it to the complete upstream lineage.

The explicit loop becomes:

```text
Paper Cycle
        ↓
Paper Submission Session
        ↓
Paper Lifecycle Batch
        ↓
Paper Account Advance
        ↓
Paper Loop Checkpoint
        ↓
next Paper Cycle
```

Checkpoint V0.1 stores nothing. It returns JSON in memory/stdout only.

## Validation before checkpoint creation

The checkpoint does not trust the Account Advance report as opaque JSON.

Before creating a checkpoint it:

1. recomputes the deterministic Account Advance id;
2. requires exact advance-id confirmation;
3. parses the emitted `next_account_input`;
4. rematerializes Paper Account V0.1 from that input;
5. verifies the resulting snapshot exactly matches the Advance report;
6. recomputes current Portfolio Admission-compatible exposures;
7. verifies the exposure list exactly matches the Advance report.

Any mismatch fails closed.

## Portable lineage

Checkpoint id binds:

- Account Advance id;
- Lifecycle Batch id;
- previous account snapshot id;
- next account snapshot id;
- SHA-256 of `next_account_input`;
- SHA-256 of current Portfolio existing exposures;
- SHA-256 of the exact Paper Account policy used to rematerialize the checkpoint.

The same verified Advance report therefore produces the same checkpoint id.

The Account policy is carried explicitly so a later Resume cannot silently use
different insolvency, mark-coherence or exposure-export semantics.

## Next-cycle boundary

A checkpoint contains:

- canonical `next_account_input`;
- current account snapshot;
- current Portfolio existing exposure;
- `next_cycle_allowed`.

For an active account:

```text
next_cycle_allowed = true
```

For an insolvent account:

```text
next_cycle_allowed = false
```

Checkpoint readiness itself does not submit or schedule a new Paper Cycle.

The next cycle still requires an explicit invocation.

Paper Loop Resume V0.1 is the governed downstream consumer: it validates the
checkpoint id, reuses the carried Account policy and passes the verified
`next_account_input` into the existing Paper Cycle engine.

## No persistence

V0.1 deliberately does not write:

- local files;
- R2;
- database rows;
- PaperBroker state;
- account state;
- workflow artifacts as authority.

A caller may save the emitted JSON externally, but that storage action is not
authorized or performed by this module.

A future persistent checkpoint store would require a separate versioned
authority.

## CLI

```bash
PYTHONPATH=src python scripts/create_paper_loop_checkpoint_v0_1.py \
  --advance-report /tmp/paper-account-advance-report.json \
  --confirm-advance-id paper-account-advance-v0-1-...
```

The CLI prints the complete checkpoint JSON.

## Explicit non-goals

V0.1 does not:

- query Binance, Pionex or MAX;
- access R2;
- access replacement holdout;
- persist state;
- schedule cycles;
- prepare candidates;
- submit paper orders;
- simulate fills;
- mutate strategy or risk;
- enable SHORT paper execution;
- create real-money orders;
- enable live trading.

## Authority

Paper Loop Checkpoint V0.1 authorizes only deterministic portable handoff
creation from one successful Account Advance report.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic cycle, automatic/scheduled submission, SHORT paper execution, formal
trade-plan authority, real-money order authority or live-trading authority.
