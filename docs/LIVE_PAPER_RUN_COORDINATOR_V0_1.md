# Live Paper Run Coordinator V0.1

Status date: 2026-09-19

Status: **PREPARED EXPLICIT PERSISTENT COORDINATION ONLY / NO REAL ORDER PATH**

## Purpose

Live Paper Simulation V0.1 already knows how to advance one simulated market
tick. Live Paper Run Coordinator V0.1 adds the durable run-control layer around
that existing engine.

It answers:

> How can one Live Paper run be stopped, restarted and continued without
> inventing a second trading engine or trusting an in-memory process?

V0.1 remains explicit/manual. It does not add a schedule.

## Append-only run ledger

The Coordinator stores immutable objects through Paper Run Store V0.1:

- `live-run/<run_id>` — deterministic run header;
- `live-state/<state_id>` — prior and next verified Live Paper states;
- `live-tick/<tick_id>` — complete Live Paper tick report;
- `live-run-step/<step_id>` — self-verifying run step;
- `live-run-result/<request_id>` — immutable committed-request result pointer.

There is intentionally no mutable `latest` object in V0.1.

That removes a common R2 split-brain problem where two workers race to overwrite
one current-state pointer.

## Run identity

`run_id` binds:

- explicit `run_name`;
- initial verified Live Paper `state_id`.

A continued step must preserve the same run id and initial-state anchor.

## Step chaining

The first committed step has:

```text
sequence = 1
previous_step_id = null
```

Every later step must have:

```text
sequence = previous.sequence + 1
previous_step_id = exact previous committed step id
previous_state_id = exact previous next_state_id
```

Before continuation, the Coordinator:

1. fully verifies the previous run step;
2. fully verifies the embedded next Live Paper state;
3. reads that same state from Run Store;
4. requires stored bytes to match the previous step;
5. only then invokes the existing Live Paper tick engine.

## Serialized Live Paper tick verification

V0.1 adds
`live_paper_tick_report_id_from_mapping()`.

The Coordinator therefore does not trust a serialized `tick_id` blindly. It
revalidates:

- tick schema and identifiers;
- next Live Paper state;
- Checkpoint lineage;
- tick timestamp;
- provider/write counters;
- closed private/holdout/real-trading authority;
- deterministic tick id.

The complete tick report is also SHA-256 bound by the run step.

## Request replay

One request id binds:

- run id;
- sequence;
- previous step id;
- previous state id;
- tick timestamp;
- canonical candidate specs SHA.

After a step is fully committed, the Coordinator writes an immutable
`live-run-result/<request_id>`.

If exactly the same request is retried later, V0.1:

1. loads the committed result;
2. loads and fully verifies its run step;
3. returns `COMMITTED_STEP_REPLAYED`;
4. performs **zero new provider requests**.

This makes ordinary completed-request retry safe.

## Crash boundary

Run Store V0.1 is append-only but is not a transactional database.

A process crash after provider evidence is fetched but before the immutable
request-result seal is stored can leave partial evidence objects.

V0.1 deliberately does not hide that condition behind a mutable pointer.
Operator review is required if a retry after such an interrupted commit sees
changed provider evidence.

Live Paper Run Recovery / Reconciliation V0.1 now provides the bounded
non-provider recovery path for this boundary. It can repair only a missing
immutable request-result seal after the complete step/state/tick evidence all
verify. It never refetches market data or rewrites state/tick/step evidence.

A future version may still introduce a transactional lease /
compare-and-swap layer if a storage backend can prove those semantics.

## Candidate boundary

Coordinator V0.1 does not generate candidates.

`candidate_specs` are still explicit inputs accepted by Live Paper V0.1.

Strategy Research Scorecard V0.1 remains a research-priority report and is not
automatically connected to candidate selection.

Binding fields:

```text
automatic_candidate_generation_authorized = false
scorecard_auto_selection_authorized = false
```

## Persistence backends

The Coordinator reuses Paper Run Store V0.1:

- explicit Local JSON;
- Cloudflare R2.

It does not add a third storage implementation.

R2 secrets remain environment / secret-manager inputs and are never serialized
into run state, steps or reports.

## CLI

Bootstrap one run with an input containing `initial_state`:

```bash
PYTHONPATH=src python scripts/run_live_paper_coordinator_v0_1.py \
  --input /tmp/live-paper-run-input.json \
  --store-backend local \
  --local-root /absolute/path/to/paper-run-store
```

Continue a run with an input containing `previous_step_id` and the same store.

Input schema:

```json
{
  "schema": "qookey-live-paper-run-coordinator-input-v0.1",
  "run_name": "primary-live-paper",
  "tick_time_ms": 0,
  "candidate_specs": [],
  "initial_state": null,
  "previous_step_id": "live-paper-run-step-v0-1-..."
}
```

Exactly one of `initial_state` / `previous_step_id` must be supplied.

## Manual GitHub workflow

`.github/workflows/live-paper-run-coordinator-v0-1.yml` is manual-only.

It:

- checks out the requested input JSON;
- uses R2 credentials only from GitHub Secrets;
- runs exactly one Coordinator step;
- uploads the stdout Coordinator report as secondary GitHub Artifact evidence.

It has no `schedule:` trigger.

## Authority

Authorized:

- current public market data;
- Live Paper simulation;
- paper-state persistence;
- append-only run coordination;
- committed-request replay.

Not authorized:

- automatic schedule;
- automatic candidate generation;
- Scorecard automatic strategy selection;
- private exchange account/order APIs;
- replacement holdout;
- real-money orders;
- real live trading.
