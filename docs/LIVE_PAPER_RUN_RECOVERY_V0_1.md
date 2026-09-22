# Live Paper Run Recovery / Reconciliation V0.1

Status date: 2026-09-19

Status: **PREPARED AUDIT + RESULT-SEAL REPAIR ONLY / NO PROVIDER REPLAY**

## Purpose

Live Paper Run Coordinator V0.1 uses an append-only ledger instead of a mutable
latest pointer. That keeps normal continuation deterministic, but a process can
still crash between immutable writes.

Recovery / Reconciliation V0.1 inspects those stored objects and answers:

- is this run internally consistent and safe to continue?
- did the process stop before any committed step existed?
- is a complete step present but its final request-result seal missing?
- is evidence incomplete, forked or ambiguous and therefore unsafe to repair?

The recovery layer does not call Pionex or any other market provider.

## Read-only discovery

Paper Run Store V0.1 now exposes read-only object-id listing by kind.

Local JSON lists only `<root>/<kind>/*.json`.

R2 lists only the exact
`paper-run-store/v0.1/<kind>/` prefix through the existing R2 adapter.

This is evidence discovery only. Listing grants no execution authority.

## Objects inspected

For one explicit `run_id`, Recovery checks:

- `live-run/<run_id>`
- all matching `live-run-step/*`
- every referenced `live-state/*`
- every referenced `live-tick/*`
- matching `live-run-result/*`

Every object is reverified with the same deterministic validators used by the
Coordinator / Live Paper runtime.

## Run-chain rules

The step chain must be contiguous:

```text
sequence 1
  previous_step_id = null
  previous_state_id = run.initial_state_id

sequence N
  previous_step_id = exact step N-1 id
  previous_state_id = exact step N-1 next_state_id
```

Duplicate sequence numbers, broken previous-step lineage or broken state
lineage produce `REVIEW_REQUIRED`.

Recovery never chooses one side of a fork automatically.

## Safe repair boundary

V0.1 authorizes exactly one repair:

> create a missing immutable `live-run-result/<request_id>` seal when the
> complete run step, previous state, next state and persisted tick all exist and
> fully verify.

The repair performs:

- zero provider requests;
- zero live market-data requests;
- zero account-state mutations;
- zero state rewrites;
- zero tick rewrites;
- zero step rewrites.

It writes only the canonical request-result seal already implied by the fully
verified step.

## What is not repairable automatically

The following are review-only:

- missing referenced state;
- missing persisted tick;
- invalid/tampered step;
- duplicate/forked sequence;
- result pointing at the wrong step;
- result without a matching step;
- ambiguous valid orphan tick after the run's terminal state.

These cases may indicate a crash after provider evidence was materialized but
before the append-only commit completed.

V0.1 does not refetch current market data to guess what the interrupted result
"should have been".

## States

Possible report states:

- `RUN_CONSISTENT`
- `RUN_EMPTY_RETRY_FROM_INITIAL_STATE_SAFE`
- `MISSING_RESULT_SEALS_REPAIRABLE`
- `MISSING_RESULT_SEALS_REPAIRED`
- `REVIEW_REQUIRED`
- CLI-level `REJECT`

## CLI

Audit only:

```bash
PYTHONPATH=src python scripts/reconcile_live_paper_run_v0_1.py \
  --run-id live-paper-run-v0-1-... \
  --store-backend local \
  --local-root /absolute/path/to/paper-run-store
```

Repair only missing result seals:

```bash
PYTHONPATH=src python scripts/reconcile_live_paper_run_v0_1.py \
  --run-id live-paper-run-v0-1-... \
  --store-backend r2 \
  --repair-missing-result-seals
```

R2 credentials remain environment / secret-manager inputs.

## Manual GitHub workflow

`.github/workflows/live-paper-run-recovery-v0-1.yml` is manual-only.

It accepts:

- exact run id;
- audit-only vs missing-result-seal repair mode.

The workflow uploads the recovery report as secondary Artifact evidence even
when the report requires review.

It has no schedule trigger and performs no provider call.

## Run Slot Claim awareness

When Run Slot Claim V0.1 evidence is present, Recovery also scans
`live-run-claim/<slot_id>` objects.

- a claim with no complete verified matching step is `REVIEW_REQUIRED`;
- a claim cannot expire or be taken over;
- Recovery never retries the provider because of a claim;
- a claim that matches a complete verified step does not block the existing
  missing-result-seal repair;
- the repair still writes only `live-run-result/<request_id>`.

Historical runs without claim objects remain valid under the original V0.1
recovery rules.

## Authority

Authorized:

- read-only Run Store evidence discovery;
- deterministic run reconciliation;
- repair of missing immutable request-result seals only.

Not authorized:

- market-provider access;
- live market-data refetch;
- account mutation;
- state/tick/step rewrite;
- fork auto-resolution;
- automatic schedule;
- private exchange APIs;
- replacement holdout;
- real-money orders;
- real live trading.
