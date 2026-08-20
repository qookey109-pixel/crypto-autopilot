# V0.11 Post-Window Execution Package

Status: **PREPARED ONLY — PRODUCTION R2 EVALUATION NOT AUTHORIZED**

Machine-readable authority-preparation file:

`config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json`

This package exists so the project does not have to invent the V0.11 production-evaluation procedure after seeing V0.10 production metadata. It freezes the procedure now, before the production window opens, without reading any production evidence.

## Current boundary

Nothing in this package authorizes production R2 access.

Current state remains:

- `V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False`;
- replacement holdout = `FROZEN_UNOPENED`;
- production R2 receipt listing/reads = not authorized;
- raw provider-object reads = forbidden;
- provider / Render requests = not authorized by V0.11;
- R2 writes / deletes = forbidden;
- source switch = false;
- Trade-Kline W1 = not authorized;
- real-money orders / live trading = forbidden.

## Earliest future execution-authority point

The frozen V0.10 metadata window ends at:

`2026-09-04T01:59:59.999Z`

Before that instant, the project must not create a production V0.11 execution authority and must not read production R2 receipts for stability evaluation.

## Required future sequence

After the full window ends:

1. Confirm the capture window is complete without reading production R2.
2. Verify V0.10 critical-path integrity and investigate any unresolved runtime drift.
3. Create a **separate, versioned V0.11 production-evaluation execution authority**.
4. Merge that authority through protected `main` after required CI.
5. Only after the authority is effective may the evaluator construct an R2 client and list/read the exact allowlisted V0.10 `receipt.json` objects.
6. Evaluate the already-frozen 194-slot semantics without post-hoc changes.
7. Emit a sanitized PASS/FAIL result without increment values or raw provider payloads.
8. Freeze that exact result as a Repository receipt.
9. Keep replacement holdout unopened until another separate versioned holdout-access authority exists.

## Future input allowlist

Even after a future V0.11 execution authority exists, the evaluator may read only:

`metadata/provider-equivalence/v0_7/render-forward-holdout-20260828/capture/slot=YYYYMMDDTHH0000Z/run=NUMERIC_RUN_ID/receipt.json`

It may not read the corresponding raw provider `.json.gz` objects and may not list/read holdout objects.

## Frozen failure semantics

The following remain fail-closed:

- missing required hourly slot;
- invalid V0.10 receipt;
- normalized-vector SHA mismatch;
- same-slot vector disagreement;
- cross-window vector drift;
- unexpected receipt-like key outside the allowlist;
- attempted raw-provider or holdout-object access.

No missing slot may be manually backfilled or replaced after the fact.

## Synthetic rehearsal evidence

PR #153 formalized and executed a 12-scenario synthetic rehearsal before production evidence existed.

Frozen rehearsal receipt:

`research/receipts/2026-08-21-provider-equivalence-v0-11-synthetic-failure-rehearsal-pass.json`

That rehearsal is a regression-safety PASS only. It is **not** production metadata-stability evidence and does not authorize production R2 evaluation or holdout access.
