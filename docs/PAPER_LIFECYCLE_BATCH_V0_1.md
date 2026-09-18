# Paper Lifecycle Batch Coordination V0.1

Status date: 2026-09-18

Status: **PREPARED EXPLICIT-PAPER-LIFECYCLE-BATCH-ONLY / NO AUTOMATION / NO LIVE AUTHORITY**

## Purpose

Paper Lifecycle Batch Coordination V0.1 is the explicit bridge from one accepted
Paper Submission Session into the existing single-intent Paper Fill / Order
Lifecycle V0.1 engine.

The product flow is now:

```text
Paper Cycle Orchestrator
        ↓
Paper Submission Session
        ↓
exact session-id confirmation
        ↓
complete session basket preflight
        ↓
Paper Fill / Order Lifecycle V0.1 for every accepted intent
        ↓
account_records
        ↓
Paper Account / Position State
```

Batch V0.1 does not implement a second fill engine. It reuses the existing
lifecycle parser, plan builder, simulator and evidence generator for every
session intent.

## Exact confirmation

The caller must provide the exact deterministic session id:

```text
confirmation_session_id == session_report.session_id
```

Before simulation, the session id is recomputed from the serialized accepted
session evidence.

A stale or modified session report is rejected.

## Complete-basket semantics

V0.1 requires exactly one lifecycle input for every accepted proposal in the
session.

It does not silently simulate only the proposals that have convenient market
data.

Each lifecycle input provides:

- proposal id;
- explicit target price;
- chronological normalized OHLC bars;
- explicit `available_notional_usd` per bar.

Input ordering is canonicalized by proposal id.

## No provider inference

Batch V0.1 performs no provider request.

It does not infer order-book depth from candle volume.

Every bar must explicitly provide:

```text
available_notional_usd
```

The existing lifecycle policy then applies the frozen participation, slippage,
fee, partial-fill and protective-exit rules.

## Preflight

Before simulating the first intent, Batch V0.1 verifies:

- session schema and accepted state;
- zero previous lifecycle simulations in the session report;
- zero persistent state writes;
- closed provider/R2/holdout/live authority;
- deterministic session id;
- exact session-id confirmation;
- session intent count within V0.1 bounds;
- execution-evidence and receipt proposal sets match;
- lifecycle input count equals session intent count;
- one lifecycle input per proposal;
- strict numeric target and bar fields;
- complete Paper Execution evidence passes the existing Lifecycle parser;
- execution intent proposal id matches the lifecycle input proposal id.

Any failure rejects the whole batch before lifecycle simulation begins.

## Output

A successful batch report contains:

- deterministic batch id;
- accepted session id;
- intent count;
- OPEN / CLOSED / CANCELLED status counts;
- one lifecycle result/evidence object per proposal;
- ready-to-use `account_records`.

Each account record has the exact shape consumed by Paper Account V0.1:

```json
{
  "paper_execution_evidence": {},
  "paper_lifecycle_report": {}
}
```

This removes manual evidence assembly between lifecycle simulation and account
materialization.

## Deterministic batch id

The batch id binds:

- accepted session id;
- canonical proposal ids;
- SHA-256 of every produced lifecycle report.

Reordering lifecycle inputs does not change the batch id.

## Valid mixed outcomes

One accepted session may produce different paper lifecycle outcomes across its
intents, including:

- `CLOSED`;
- `OPEN_POSITION`;
- `CANCELLED_UNFILLED`.

This is expected simulation behavior.

A valid cancellation is not converted into a workflow failure.

## CLI

```bash
PYTHONPATH=src python scripts/simulate_paper_lifecycle_batch_v0_1.py \
  --input /tmp/paper-lifecycle-batch-input.json \
  --confirm-session-id paper-session-v0-1-...
```

Input shape:

```json
{
  "schema": "qookey-paper-lifecycle-batch-input-v0.1",
  "session_report": {},
  "lifecycle_inputs": [
    {
      "proposal_id": "portfolio-v0-1-...",
      "target_price": 105.0,
      "bars": [
        {
          "time_ms": 2000,
          "open": 100.0,
          "high": 101.0,
          "low": 99.0,
          "close": 100.5,
          "available_notional_usd": 4000.0
        }
      ]
    }
  ]
}
```

The CLI performs no provider or persistent-state operation.

## Deliberate limitations

V0.1 does not:

- query Binance, Pionex or MAX;
- access R2 or replacement holdout;
- schedule lifecycle runs;
- persist lifecycle/account state;
- infer market depth;
- model funding settlement;
- model liquidation;
- model exchange rejection;
- enable SHORT paper lifecycle;
- create real exchange orders;
- enable live trading.

## Authority

Paper Lifecycle Batch Coordination V0.1 authorizes only one explicit,
caller-supplied, complete-session paper lifecycle simulation.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic/scheduled lifecycle execution, SHORT paper execution, formal
trade-plan authority, real-money order authority or live-trading authority.
