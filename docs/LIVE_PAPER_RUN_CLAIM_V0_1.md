# Live Paper Run Slot Claim V0.1

Status date: 2026-09-22

Status: **AUTHORIZED ON EXPLICIT PROTECTED-MAIN MERGE / MANUAL COORDINATOR ONLY**

## Purpose

Live Paper Run Coordinator V0.1 already replays a fully committed request without
a second provider call, and Run Recovery V0.1 can audit partial persistence.
The missing boundary is the interval before a request has a committed result:
two workers could otherwise start different requests from the same prior run
state and both reach the public market-data provider.

Run Slot Claim V0.1 closes that boundary with one atomic create-if-absent gate.

## Deterministic slot identity

One coordination slot is identified only by:

- `run_id`;
- `sequence`;
- `previous_step_id`;
- `previous_state_id`.

The slot identity deliberately excludes the requested tick timestamp and
candidate payload.

Therefore two workers starting from the same run position compete for the same
slot even when their requested tick or candidate inputs differ.

The winning immutable claim records the request evidence:

- `request_id`;
- `tick_time_ms`;
- `candidate_specs_sha256`.

## Write order

Coordinator V0.2 performs the following order for a new request:

1. verify run lineage and prior state;
2. replay an already committed identical request if present;
3. persist/replay the deterministic run header;
4. persist/replay the verified previous state;
5. atomically create `live-run-claim/<slot_id>`;
6. only after the claim succeeds, call the existing public Live Paper feed;
7. persist next state, tick, run step and committed request-result seal.

The claim uses Paper Run Store's existing create-if-absent primitive. It does
not add a storage backend or namespace outside the existing Paper Run Store.

## Conflict semantics

An existing claim is a hard conflict.

This remains true when the existing claim belongs to the exact same request.
V0.1 does not treat a claim as a lease and does not assume that the previous
worker died safely.

A conflict therefore means:

- no provider retry;
- no claim expiry;
- no claim takeover;
- no stale-writer adoption;
- no automatic conflict resolution.

A fully committed identical request is still replayed before claim acquisition,
so normal post-commit retry remains safe.

## Crash semantics

If the winning worker crashes after the claim is written but before a complete
verified step exists, the persistent claim remains.

Run Recovery V0.1 audits `live-run-claim` objects. An unresolved claim without
a complete verified matching step causes `REVIEW_REQUIRED`.

If the complete state/tick/step evidence exists and only the immutable
`live-run-result` seal is missing, the existing bounded result-seal repair
remains allowed. This repair performs no provider request and does not take over
the claim.

## Scheduling

No schedule is added.

The existing manual workflow
`.github/workflows/live-paper-run-coordinator-v0-1.yml` explicitly selects:

- `config/live_paper_run_coordinator_v0_2.json`;
- `config/live_paper_run_claim_v0_1.json`.

## Authority

Authorized on explicit merge:

- one deterministic Paper Run Store slot claim before provider access;
- Coordinator V0.2 claim enforcement;
- Recovery audit of claims;
- the already-authorized public Live Paper provider path after claim success;
- the already-authorized paper-state persistence path.

Not authorized:

- automatic schedule;
- claim expiry;
- claim takeover;
- automatic retry after conflict;
- automatic candidate generation;
- strategy auto-selection;
- new provider scope;
- new R2 namespace;
- private exchange APIs;
- holdout access;
- real-money orders;
- real live trading.
