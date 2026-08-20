# V0.10 Capture Window Operations Runbook

Status: **PREPARED / NO NEW EXECUTION AUTHORITY**

This runbook governs operational response during the frozen V0.10 metadata-capture window. It does **not** modify the V0.10 scientific protocol, authorize new provider/R2 access, authorize manual capture, or authorize any downstream holdout/trading action.

## Frozen timing

- Window start: `2026-08-27T00:00:00Z`
- Window end: `2026-09-04T01:59:59.999Z`
- 194 UTC hourly slots
- Scheduled attempts: `:17` and `:47` each hour
- Expected scheduled attempts: 388
- First scheduled attempt: `2026-08-27T00:17:00Z`
- Last scheduled attempt: `2026-09-04T01:47:00Z`
- Coverage rule: at least one complete valid capture per UTC hourly slot

## Default operating rule

The frozen scheduled workflow is the only normal execution path. Do not manually backfill missed attempts or missed hourly slots. A failed or missing slot is scientific evidence and must remain visible to the future V0.11 evaluation.

The scheduled observer may inspect GitHub Actions run/job/step metadata only. It must not read capture artifacts, production R2, provider payloads, Render payloads, or replacement-holdout data.

## Incident handling

| Situation | Required response | Forbidden response |
| --- | --- | --- |
| `:17` attempt fails | Preserve failure; observe metadata only; let the frozen `:47` attempt run normally | Manual capture/backfill; threshold change; holdout access |
| Both attempts fail in one UTC hour | Preserve both failures; continue later frozen slots only if critical path remains valid; mark the slot as potentially missing | Retroactive backfill; rewriting slot time; hiding failed runs |
| R2 8 GB headroom gate blocks | Preserve `BLOCKED`; stop before write | Raising hard stop mid-run; deleting objects to force passage; partial write |
| Render/provider transport fails | Preserve failure; wait for next frozen scheduled attempt; any critical-path repair requires separate versioned emergency authority | Unreviewed runtime/secret/provider changes; provider substitution; source splicing |
| Scheduled run is stale >30 minutes | Preserve stale skip; stop before provider/R2 access | Bypassing freshness guard; rewriting timestamps; manual backfill |
| Critical-path drift is detected | Preserve drift evidence; block unreviewed fixes; require protected-main PR plus separate versioned emergency authority before any production-critical change | Auto-fix; auto-deploy; silent baseline update; ignoring drift |

## Mid-window change policy

Default state is **NO PRODUCTION-CRITICAL MUTATION**.

If an intervention becomes unavoidable, it requires a separate versioned emergency authority and protected-main PR. The intervention must bind the pre-change and post-change SHAs, may not change frozen thresholds/scope, may not open the replacement holdout, and may not retroactively validate or backfill earlier missing slots.

## Window-end handoff

When the full window has ended, do not immediately read production R2 and do not immediately run V0.11. Follow the already-prepared `config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json` sequence:

1. confirm the full window ended without reading production R2;
2. verify critical-path integrity and runtime lineage;
3. create a separate versioned V0.11 production-evaluation execution authority;
4. merge that authority through protected `main` after CI;
5. only then allow receipt-only R2 listing/reads for the frozen V0.11 evaluator.

Replacement holdout remains `FROZEN_UNOPENED` even after a future metadata-stability PASS until a separate holdout-access authority is explicitly created and merged.

## Always forbidden by this runbook

- manual metadata-capture backfill;
- retroactive slot repair;
- lowering or changing frozen equivalence/stability thresholds;
- reading replacement-holdout candles;
- source switching or provider splicing;
- W1 materialization;
- automatic trade plans;
- real-money orders;
- live trading.
