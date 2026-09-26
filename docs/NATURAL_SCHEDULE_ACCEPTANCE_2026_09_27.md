# 2026-09-27 Natural Schedule Acceptance Checklist

Prepared on 2026-09-26 against main `fd68650472188e6cdded4d4e6aa5b1a452774f72`.

This document is an observation checklist, **not execution authority**. Before acting, re-resolve live `main`, open pull requests, workflow source, and exact run metadata. Do not use manual dispatch to substitute for missing natural schedule evidence.

## Purpose

The next fixed checkpoint is the 2026-09-27 natural Pionex observability and Core100 Weekly Training sequence. Keep the runtime baseline stable until those runs are reviewed. In particular, do not edit:

- `src/qookey/paper/live_v0_1.py` execution-chain typing paths;
- `src/qookey/training/detailed.py`;
- the Pionex observability workflow/config/authority;
- the Core100 Weekly Training workflow/fingerprint contract;
- thresholds, promotion gates, source-switch authority, holdout state, or live-trading authority.

The current type-visibility baseline is 33 diagnostics: 18 protected and 15 ordinary cleanup candidates. The 15 ordinary candidates are the five remaining Live Paper execution-chain diagnostics plus ten `training/detailed.py` diagnostics. Resume those slices only after the natural evidence below is reviewed.

## Current pre-check evidence

| Item | Latest reviewed natural evidence before this checklist | Interpretation |
| --- | --- | --- |
| Pages | Run `36232991943`, schedule, success, head `fd68650472188e6cdded4d4e6aa5b1a452774f72` | Current-main scheduled dashboard pipeline completed successfully. |
| Research Automation Health | Run `36228511162`, schedule, success | Latest reviewed Health schedule was healthy; do not dispatch a replacement for later missing slots. |
| Pionex observability | Run `35500652150`, 2026-09-20 schedule, success | Prior bounded observability evidence exists; 2026-09-27 remains the next fixed natural checkpoint. |
| Core100 weekly | Run `35502249846`, 2026-09-20 schedule, success under the previous workflow display name | Historical weekly evidence only. The 2026-09-27 run must be evaluated against the current V0.2 successor implementation. |
| Core100 V0.2 bootstrap | Run `36110721415`, workflow_dispatch, success | One-time bootstrap is consumed; it must not be rerun. Model quality remains separate and rejected. |

## Nominal 2026-09-27 sequence

Times are Asia/Taipei. GitHub schedule delivery can be delayed; the nominal time is not a completion deadline.

| Nominal time | Workflow | Required evidence |
| --- | --- | --- |
| 11:53 | Pionex Alternative Assets Observability V0.2 | Natural `schedule` event, exact head SHA, run/attempt, job conclusion, secret-free report artifact, report status and safety-boundary fields. |
| 12:37 | Binance USD-M Crypto Core 100 Training V0.2 | Natural `schedule` event, exact head SHA, run/attempt, report artifact, fingerprint comparison result, training/R2/provider flags. |
| 12:43 | Dashboard GitHub Pages | Record whether the natural schedule ran and whether build/deploy/browser-production actually executed; skipped jobs are not PASS evidence. |
| 12:57 | Research Automation Health V0.2 | Natural schedule result, exact head, overall result, alert count and schedule coverage. |
| after Health | Cloud Project Maintenance V0.1 | Only a same-repository natural Health schedule may trigger it. Record inspect/propose result or NO_CHANGE; do not manufacture replacement evidence. |

## Pionex acceptance

Record:

- run ID and attempt;
- event = `schedule`;
- exact `head_sha`;
- workflow/job conclusion;
- artifact ID/name;
- report `status`;
- `catalog_validation_status`;
- `catalog_diff_status`;
- `provider_requests_performed`;
- R2 latest-pointer/readback result;
- authority/safety-boundary booleans.

Interpretation:

- `PASS`: record the bounded evidence; this does not authorize source switch, model promotion, trade plans, orders, or live trading.
- `REVIEW_REQUIRED`: preserve the report and review the catalog difference; do not widen scope automatically.
- `SKIPPED`: verify the window/guard reason and confirm zero provider requests and no R2 access. Do not manually rerun merely to replace natural evidence.
- workflow failure: preserve the failed run and classify the concrete failure before any code change.

The existing V0.2 schedule window expires 2026-10-01 08:00 Asia/Taipei. No automatic extension is authorized.

## Core100 Weekly Training acceptance

Record:

- run ID and attempt;
- event = `schedule`;
- exact `head_sha`;
- report artifact ID/name;
- dataset fingerprint;
- experiment/model fingerprint;
- runtime guard fingerprint where present;
- report `status`;
- `training_performed`;
- `r2_writes_performed`;
- `provider_requests_performed`;
- model-quality result, if emitted.

Interpretation:

- `NO_CHANGE`: require `training_performed=false`, `r2_writes_performed=false`, and `provider_requests_performed=0`. This is the expected deduplication path only if the governed fingerprints are unchanged.
- `PASS`: preserve the new evidence and inspect why the fingerprint changed. PASS is pipeline evidence, not automatic model acceptance.
- `REVIEW_REQUIRED`: stop for review; do not loosen a gate or rerun until the reason is understood.
- `SKIPPED`: confirm the explicit guard reason and zero unauthorized activity.

Do not rerun the consumed V0.2 bootstrap. Do not infer promotion, threshold change, source switch, holdout opening, or live trading from workflow success.

## Follow-up acceptance

After Pionex and Weekly Training:

1. Re-resolve `main` and verify the natural runs belong to the intended default-branch state.
2. Review Pages separately: build, deployment and browser-production each need their own conclusion.
3. Review the subsequent Health natural run. Preserve delayed/missing slots as observations instead of replacing them with dispatch evidence.
4. Review Cloud Maintenance only if it was triggered by the qualifying natural Health run.
5. Update status documentation with exact run IDs, attempts, head SHAs and artifact IDs.
6. Only then reopen TD-007 ordinary cleanup for the five Live Paper execution-chain diagnostics and ten `training/detailed.py` diagnostics.

## Decision ledger

| Check | Run ID | Head SHA | Result | Artifact / evidence | Next action |
| --- | --- | --- | --- | --- | --- |
| Pionex 11:53 | pending | pending | pending | pending | wait for natural schedule |
| Core100 12:37 | pending | pending | pending | pending | wait for natural schedule |
| Pages 12:43 | pending | pending | pending | pending | verify build/deploy/browser separately |
| Health 12:57 | pending | pending | pending | pending | verify alerts and coverage |
| Cloud Maintenance | pending | pending | pending | pending | record NO_CHANGE/proposal only if naturally triggered |

## Boundaries

Budget remains FREE-ONLY / 0 USD per month. The project remains PAPER / LIVE-PAPER ONLY. Replacement holdout remains frozen and unopened. `source_switch_authorized=false`. Do not write secrets to repository content, logs, artifacts, or chat.
