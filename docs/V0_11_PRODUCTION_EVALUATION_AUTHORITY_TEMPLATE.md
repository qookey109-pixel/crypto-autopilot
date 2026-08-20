# V0.11 Production Evaluation Authority Template

Status: **TEMPLATE PREPARED / EXECUTION NOT AUTHORIZED**

This document defines how the future V0.11 production metadata-stability evaluation authority must be constructed after the full V0.10 metadata-capture window ends. It does not authorize production R2 access now.

## Earliest creation point

The actual authority may not be created or merged before `2026-09-04T01:59:59.999Z` has passed. Before the actual authority is merged, no V0.11 production R2 client may be constructed and no production receipt may be listed or read.

Before authority creation, review V0.10 critical-path integrity and all mid-window interventions. Any unreviewed production-critical drift fails this gate.

## Exact evaluator lineage

The future authority must bind the frozen V0.11 protocol and implementation, including:

- `config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json` blob `58bf122d27804a8c61149743ae8c9afca42aca87`;
- `src/crypto_autopilot/provider_metadata_stability_v0_11.py` blob `9ea9cdbf626fa9ecde2f17f748e1807cd6cd09d5` before execution enablement;
- `config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json` blob `be34e426f8305b2dc940a3354506802008302900`.

Any scientific-semantic drift requires a new versioned review instead of silently updating these bindings.

## Only execution delta that may be authorized

After the separate future authority is merged, the reviewed one-shot evaluation may construct an R2 client, list allowlisted V0.10 `receipt.json` objects, read those receipt objects, and execute the frozen V0.11 evaluator.

The execution path must remain one-shot and reviewed. Do not add a schedule or automatic post-window evaluation.

## What must remain forbidden

The future V0.11 execution authority must not authorize R2 writes/deletes, raw provider-object reads, provider/Render requests, `METADATA_RELAY_TOKEN`, holdout listing/reading/evaluation, retroactive slot backfill, post-hoc deadbands/scope changes, provider splicing, source switch, W1 materialization, backtest admission, strategy changes, automatic trade plans, real-money orders, or live trading.

The future production workflow may bind only the R2 credentials required for receipt-only read access. It must not bind the metadata relay token and must not add provider or Render network access.

## Required PR lineage

The future authority must record the reviewed `main` SHA, exact capture-window completion statement, critical-path integrity evidence, exact protocol/runtime hashes, exact receipt namespace/pattern, 194-slot / 15-symbol / 45-pair scope, PR number/head SHA, required CI results, and post-merge `main` SHA.

## Result boundary

The V0.11 result remains sanitized: no increment values, raw provider payloads, or holdout values. Missing slots, invalid receipt keys, same-slot disagreements, drift-provider names, counts, and stable vector SHA-256 values may be emitted as allowed by the frozen protocol.

A future stability PASS still does **not** authorize holdout access. A separate versioned holdout-access authority remains mandatory.
