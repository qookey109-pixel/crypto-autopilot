# Paper Loop Integrity / Multi-Cycle Replay V0.1

Status date: 2026-09-18

Status: **PREPARED AUDIT-ONLY / NO EXECUTION / NO LIVE AUTHORITY**

## Purpose

Paper Loop Integrity V0.1 verifies that two or more complete forward paper-loop
rounds form one continuous deterministic lineage.

A complete audited round is:

```text
start Checkpoint
        ↓
Resume
        ↓
ready Paper Cycle
        ↓
Paper Submission Session
        ↓
Paper Lifecycle Batch
        ↓
Paper Account Advance
        ↓
end Checkpoint
```

The next round must begin from the exact end Checkpoint of the prior round.

Integrity V0.1 does not execute any stage. It audits already-produced reports.

## Multi-cycle requirements

V0.1 requires at least two complete forward rounds.

For every round it recomputes and verifies:

- start Checkpoint id;
- Resume id;
- embedded Cycle id;
- Session id;
- Lifecycle Batch id;
- Account Advance id;
- end Checkpoint id.

It also verifies the cross-stage links:

- Resume checkpoint = round start checkpoint;
- Cycle account snapshot = start checkpoint snapshot;
- Cycle existing exposure = start checkpoint exposure;
- Session cycle id = audited Cycle id;
- Batch session id = audited Session id;
- Advance batch id = audited Batch id;
- Advance previous snapshot = start checkpoint snapshot;
- end Checkpoint advance/batch/snapshot lineage = audited Advance.

## Cross-round continuity

For round N+1:

```text
round[N+1].start_checkpoint
==
round[N].end_checkpoint
```

V0.1 compares the complete canonical Checkpoint payload, not only the id.

The account snapshot timestamp may stay equal or advance, but it may never move
backward.

## Forward identity rules

Distinct forward rounds must not reuse:

- Cycle ids;
- Session ids;
- Batch ids;
- Advance ids;
- newly submitted paper intent ids.

A forward round must also produce a different end Checkpoint identity from its
start Checkpoint.

This keeps exact replay separate from a new trading round.

## Replay semantics

Deterministic replay is tested by auditing the exact same transcript again.

The same transcript must produce the same:

- transcript SHA-256;
- round summaries;
- integrity id.

Replay does not create a second Account record and is not counted as an
additional forward round.

Existing Account Advance idempotency rules remain responsible for preventing
duplicate lifecycle accounting.

## Integrity anchors

The audit input must declare:

- expected first Checkpoint id;
- expected terminal Checkpoint id.

Both are checked against the actual transcript.

This prevents a valid middle fragment from being presented as a different
anchored chain.

## Output

A successful report has:

```text
MULTI_CYCLE_INTEGRITY_PASS
```

and includes:

- deterministic integrity id;
- transcript SHA-256;
- round count;
- start / terminal Checkpoint ids;
- start / terminal snapshot ids;
- start / terminal paper equity;
- descriptive net equity change;
- count of unique forward intents;
- per-round Cycle / Session / Batch / Advance ids;
- per-round snapshot timestamps and equity change.

Equity change is descriptive audit information only. It is not a strategy
score, edge claim or profitability verdict.

## CLI

```bash
PYTHONPATH=src python scripts/audit_paper_loop_integrity_v0_1.py \
  --input /tmp/paper-loop-integrity-input.json
```

Input shape:

```json
{
  "schema": "qookey-paper-loop-integrity-input-v0.1",
  "expected_start_checkpoint_id": "paper-loop-checkpoint-v0-1-...",
  "expected_terminal_checkpoint_id": "paper-loop-checkpoint-v0-1-...",
  "rounds": [
    {
      "start_checkpoint": {},
      "resume_report": {},
      "session_report": {},
      "lifecycle_batch_report": {},
      "account_advance_report": {},
      "end_checkpoint": {}
    }
  ]
}
```

The default policy requires 2–8 complete rounds.

## Explicit non-goals

Integrity V0.1 does not:

- prepare candidates;
- resume a checkpoint;
- submit paper orders;
- simulate lifecycle bars;
- advance account state;
- write checkpoints;
- query providers;
- access R2 or replacement holdout;
- rank strategies;
- place real-money orders;
- enable live trading.

## Authority

Paper Loop Integrity V0.1 is audit-only.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic execution, strategy-ranking authority, real-money order authority or
live-trading authority.
