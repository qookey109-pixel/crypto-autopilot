# Paper Account Advance V0.1

Status date: 2026-09-18

Status: **PREPARED EXPLICIT-ACCOUNT-REMATERIALIZATION-ONLY / NO PERSISTENCE / NO LIVE AUTHORITY**

## Purpose

Paper Account Advance V0.1 closes the explicit paper loop after Lifecycle Batch.

It consumes:

- the previous complete Paper Account V0.1 input;
- one complete Paper Lifecycle Batch V0.1 report;
- an exact batch-id confirmation;
- fresh marks for every position that remains open after the batch.

It then creates the next deterministic Paper Account snapshot and emits the
next complete account input for another Paper Cycle.

The flow is:

```text
previous Paper Account input
        ↓
Paper Lifecycle Batch
        ↓
exact batch-id confirmation
        ↓
latest-record merge by paper intent
        ↓
Paper Account V0.1 rematerialization
        ↓
next_account_input
        ↓
next Paper Cycle
```

V0.1 writes no database, file, broker state or R2 object.

## Why replacement is required

Paper Lifecycle Batch may re-simulate an existing accepted intent with a longer
causal bar sequence.

For example:

```text
first lifecycle evidence:
OPEN_POSITION at t=2000

later lifecycle evidence:
CLOSED at t=3000
```

The account must not keep both reports. Doing so would count the same intent
twice.

Paper Account Advance therefore keys records by paper execution `intent_id`
and keeps exactly one latest lifecycle record per intent.

## Existing-intent transition rules

For an intent already present in the previous account:

- lifecycle id must remain identical;
- identical lifecycle report replay is allowed and produces no account change;
- later lifecycle evidence may replace the previous report;
- lifecycle event time may not move backward;
- a different report at the exact same last-event timestamp is rejected;
- changing lifecycle id for the same paper intent is rejected.

Because lifecycle id binds intent, stop and explicit target, V0.1 does not allow
retargeting an already accepted paper intent through account replacement.

A new target requires a separate future governance path rather than silently
rewriting existing lifecycle identity.

## Batch lineage

Before merging records, Account Advance verifies:

- Lifecycle Batch schema/state;
- zero provider requests;
- zero persistent-state writes;
- closed R2/holdout/automatic/live authority;
- deterministic batch id;
- exact batch-id confirmation;
- batch result proposal ids;
- lifecycle ids;
- outer result status/reason against the inner lifecycle result;
- Account record proposal/lifecycle pairing.

A modified Batch report with a stale id is rejected.

## Previous account validation

The previous account input is not trusted as opaque state.

It is parsed and fully rematerialized through Paper Account V0.1 before any
advance occurs.

This validates:

- execution receipt lineage;
- lifecycle accounting;
- existing marks;
- existing open-position boundaries;
- prior cash/equity reconstruction.

The original `initial_equity_usd` is preserved.

Account Advance does **not** use the previous account equity as a new initial
balance.

## Next marks

After records are merged, the next account is rematerialized from the complete
latest-record set.

Fresh marks must match every position that remains `OPEN_POSITION` exactly.

If the batch closes all positions, the next mark list is empty.

If an open position remains, a current mark is required and the normal Account
V0.1 protective-boundary checks still apply.

## Idempotent replay

Applying an identical batch record to an account that already contains that
exact lifecycle report does not double-count:

```text
ACCOUNT_ADVANCE_NO_CHANGE
```

The resulting account snapshot is unchanged.

## Forward transition

When a Batch introduces:

- a new intent; or
- forward lifecycle evidence for an existing intent,

the state is:

```text
ACCOUNT_ADVANCED
```

The report records:

- added record count;
- replaced record count;
- unchanged record count;
- total record count;
- previous snapshot id;
- next snapshot id;
- exact batch id.

## Output

A successful report contains:

- deterministic advance id;
- previous and next snapshot ids;
- next Paper Account evidence;
- canonical `next_account_input`;
- current Portfolio Admission-compatible existing exposure;
- whether new portfolio capacity may be exported.

The emitted `next_account_input` is the intended input for the next manual
Paper Cycle.

## Downstream portable checkpoint

Paper Loop Checkpoint V0.1 is the optional deterministic handoff boundary after
Account Advance.

It requires exact advance-id confirmation, rematerializes the emitted account,
reconciles Portfolio exposure and carries the verified `next_account_input`
forward without persisting it.

## CLI

```bash
PYTHONPATH=src python scripts/advance_paper_account_v0_1.py \
  --input /tmp/paper-account-advance-input.json \
  --confirm-batch-id paper-lifecycle-batch-v0-1-...
```

Input shape:

```json
{
  "schema": "qookey-paper-account-advance-input-v0.1",
  "previous_account_input": {
    "schema": "qookey-paper-account-state-input-v0.1",
    "initial_equity_usd": 100.0,
    "records": [],
    "marks": []
  },
  "lifecycle_batch_report": {},
  "next_marks": []
}
```

## Explicit non-goals

V0.1 does not:

- query Binance, Pionex or MAX;
- read/write R2;
- access replacement holdout;
- persist account state;
- persist broker state;
- schedule cycles;
- submit paper orders;
- run lifecycle simulation;
- mutate strategy or risk rules;
- enable SHORT paper execution;
- create real-money orders;
- enable live trading.

## Authority

Paper Account Advance V0.1 authorizes only explicit deterministic replacement
of latest paper lifecycle records followed by Paper Account V0.1
rematerialization.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic cycle, automatic/scheduled submission, SHORT paper execution, formal
trade-plan authority, real-money order authority or live-trading authority.
