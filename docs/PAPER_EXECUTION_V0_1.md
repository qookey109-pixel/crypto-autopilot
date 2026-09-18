# Paper Execution V0.1

Status date: 2026-09-18

Status: **PREPARED PAPER-ONLY / NO LIVE AUTHORITY**

## Purpose

Paper Execution V0.1 is the first product-stage handoff from validated strategy
research and bounded position sizing into the existing Repository Paper Broker.

It does **not** create a second broker.

The existing implementation in
`src/crypto_autopilot/exchanges/paper.py` remains the only Repository Paper
Broker boundary.

## Upstream gates

A paper intent can be prepared only when all of the following are true:

1. the strategy family exists in Multi-Strategy Library V0.1;
2. a complete Strategy Family Validation V0.1 report is supplied;
3. that report belongs to the same strategy family;
4. the family report state is
   `FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW`;
5. the family report preserves zero promotion/trading authority;
6. Risk / Position Sizing V0.1 returns `SIZING_READY`;
7. a complete Portfolio Admission V0.1 report is supplied;
8. the portfolio report state is `PORTFOLIO_ADMITTED`;
9. the exact reconstructed proposal id appears in `admitted_proposal_ids`;
10. portfolio admission authority remains closed;
11. the sizing direction is supported by the registered family;
12. the direction is currently authorized for Repository Paper Broker use.

A Router match alone is not sufficient.

## Family-validation lineage

Paper Execution does not accept only a status string.

The complete family-validation report is canonically hashed with SHA-256. The
resulting digest is included in the paper intent and therefore in the
deterministic intent id.

If family evidence changes, the intent id changes.

This prevents a stale paper intent from silently referring to different family
evidence.

## Risk handoff

Paper Execution never recalculates position size.

The following value is passed directly into the Repository Paper Broker:

```text
PositionSizingPlan.approved_notional_usd
```

The upstream stop is also preserved in the paper intent for audit lineage.

Paper Execution does not:

- tighten the stop;
- increase notional;
- consume unused target risk;
- infer leverage;
- infer exchange precision.

## Portfolio-admission lineage

Paper Execution reconstructs its exact Portfolio V0.1 proposal from the same
family-validation report, symbol, strategy family, timestamp and sizing plan.

The complete portfolio-admission report must:

- use schema `qookey-portfolio-admission-report-v0.1`;
- have state `PORTFOLIO_ADMITTED`;
- include the reconstructed proposal id in `admitted_proposal_ids`;
- not mark that proposal rejected;
- preserve zero strategy-ranking, subset-selection, PaperBroker and live authority.

The complete portfolio report is SHA-256 hashed and bound into the paper intent.
A changed portfolio basket or authority record therefore changes the paper
intent id.

## Deterministic idempotency

The paper intent id is a SHA-256-derived identifier over:

- symbol;
- registered strategy family;
- family-validation report SHA-256;
- portfolio proposal id;
- portfolio-admission report SHA-256;
- review state;
- direction;
- as-of timestamp;
- entry price;
- stop price;
- approved notional;
- target risk;
- realized risk;
- risk-utilization fraction.

The existing PaperBroker uses that intent id as its `order_id`.

Submitting the same intent twice returns the same order and leaves only one
PaperBroker record.

## V0.1 direction authority

### LONG

Explicit Repository Paper Broker LONG intent recording is enabled in V0.1.

This means an explicitly invoked local/repository paper action may call
`PaperBroker.submit_long()`.

It does **not** mean automatic scheduling or real exchange submission.

### SHORT

SHORT research sizing exists upstream, but Paper Execution V0.1 keeps:

```text
short_paper_execution_authorized = false
```

A SHORT sizing plan therefore returns:

```text
NO_EXECUTION / short_paper_execution_not_authorized
```

The current PaperBroker has no SHORT submit path and V0.1 does not invent one.

## Existing Paper Broker limitations

The existing broker is an intent recorder, not a realistic fill simulator.

It does not yet model:

- order-book fills;
- slippage;
- partial fills;
- funding settlement;
- liquidation;
- exchange rejection;
- persistent broker state;
- stop/target monitoring.

Those are separate later paper-simulation/execution concerns.

## Local integration CLI

A no-network integration command is provided:

```bash
PYTHONPATH=src python scripts/run_paper_execution_v0_1.py \
  --symbol BTC_USDT_PERP \
  --strategy-family TREND_FOLLOWING \
  --family-validation-report /tmp/trend-family-report.json \
  --portfolio-admission-report /tmp/portfolio-admission-report.json \
  --direction LONG \
  --equity-usd 100 \
  --entry-price 100 \
  --stop-price 99 \
  --as-of-ms 1000
```

This command:

1. loads the versioned Risk V0.1 policy;
2. calculates the sizing plan;
3. loads the complete family-validation report;
4. loads a separately produced Portfolio Admission V0.1 report;
5. reconstructs and verifies the exact admitted portfolio proposal;
6. prepares the deterministic paper intent;
7. submits it to a new in-memory Repository Paper Broker instance if all gates
   pass;
8. prints deterministic JSON evidence.

It performs no provider request, R2 operation, holdout read, persistent broker
write or exchange call.

## Automatic execution remains closed

V0.1 explicitly keeps:

- automatic submission unauthorized;
- scheduled paper execution unauthorized;
- provider access unauthorized;
- R2 access unauthorized;
- holdout access unauthorized;
- strategy/model promotion unauthorized;
- formal trade-plan authority closed;
- real-money orders unauthorized;
- live trading unauthorized.

Therefore this stage creates the paper-execution contract and explicit local
integration path without enabling an unattended trading loop.

## Next stage

Portfolio Admission V0.1 is now upstream of this contract.

Future work may separately add:

- a validated subset/allocation optimizer with explicit ranking evidence;
- measured point-in-time correlation/covariance;
- a realistic paper fill/settlement simulator;
- unattended paper orchestration under separate authority.

None of those is implied by V0.1 paper intent recording.

## Authority

Paper Execution V0.1 grants authority only for explicit LONG intent recording in
the existing Repository Paper Broker under the frozen V0.1 gates.

It grants no SHORT paper execution, automatic/scheduled submission, provider
access, R2 access, replacement-holdout access, source switch, strategy/model
promotion, formal trade plan, real-money order or live-trading authority.
