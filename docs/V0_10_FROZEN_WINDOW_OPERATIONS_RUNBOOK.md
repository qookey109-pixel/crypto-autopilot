# V0.10 Frozen Window Operations Runbook

Status: **PRE-WINDOW MAINTENANCE / OPERATIONAL GUIDANCE ONLY**

Tracker: Issue #149

This runbook governs operational response during the frozen V0.10 metadata-capture window without changing scientific scope or execution authority.

## Authority boundary

Repository `main` remains the formal authority. This document does not authorize any new provider access, R2 access, holdout access, source switch, strategy change, Trade-Kline W1 materialization, real-money order, or live trading.

Current frozen execution authority remains:

- workflow: `.github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml`;
- window: `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`;
- 194 UTC hourly slots;
- scheduled attempts at UTC `:17` and `:47` only;
- Render Free / Frankfurt V0.10 transport;
- Render Auto-Deploy OFF;
- replacement holdout: `FROZEN_UNOPENED`;
- V0.11 production R2 evaluation: `NOT_AUTHORIZED`;
- `source_switch_authorized=false`;
- project remains PAPER ONLY.

## Normal successful scheduled attempt

For an in-window scheduled run, normal health requires the V0.10 pipeline to complete:

1. `validate-atomic-cutover`;
2. `window-gate`;
3. freshness guard;
4. capture step;
5. capture-boundary assertion.

The read-only observer may report pipeline execution health based on GitHub Actions run/job/step metadata. Observer PASS is operational only and is not a provider-metadata equivalence result or V0.11 stability result.

The capture artifact may be inspected only as allowed by the already-authorized operational monitoring path. Direct production R2 reads are not authorized before a separate post-window V0.11 execution authority exists.

## `:17` attempt fails or is skipped

If the first scheduled attempt for an hourly slot fails, is cancelled, or is rejected by the freshness guard:

- do not manually rerun the workflow;
- do not dispatch a manual V0.10 capture;
- do not modify the schedule;
- do not create an ad-hoc replacement capture path;
- do not change provider, endpoint, proxy, credentials, or runtime tier;
- allow the already-frozen `:47` scheduled attempt to proceed normally.

A failure of the `:17` attempt does not by itself authorize intervention into capture evidence.

## `:47` attempt also fails

If both frozen attempts for the same hourly slot fail or are skipped:

- record the slot as operationally missing for later authorized evaluation;
- do not create a third attempt after the fact;
- do not backfill the missing slot manually;
- do not modify timestamps or slot assignment;
- do not reinterpret a neighboring-hour capture as the missing slot;
- do not weaken V0.11 coverage requirements.

Under the frozen V0.11 evaluator semantics, a missing required slot is expected to fail closed when production evaluation is later authorized. This runbook must not manufacture replacement evidence.

## R2 FREE-only headroom gate returns BLOCKED

If a scheduled capture reports `R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE`:

- treat the attempt as fail-closed;
- verify that no R2 writes were performed according to the capture boundary result;
- do not delete historical or frozen evidence to create space;
- do not overwrite existing evidence;
- do not increase cloud spend or add a payment method;
- do not bypass the 8,000,000,000-byte hard stop;
- allow only the next already-frozen scheduled attempt to perform its own fresh headroom check.

If the second attempt is also blocked, preserve the missing-slot outcome. Do not manually create a replacement capture.

## Stale queued run

If the freshness guard reports a stale or out-of-window scheduled run:

- accept the fail-closed skip;
- do not bypass the 30-minute freshness rule;
- do not alter the run creation time or execution timestamp;
- do not manually force the capture step;
- do not treat the skipped run as valid evidence.

## Workflow or GitHub Actions failure

If validation, checkout, dependency installation, job scheduling, or GitHub Actions infrastructure fails:

- inspect run/job/step metadata and logs for diagnosis;
- do not rerun a production capture manually;
- do not modify frozen thresholds, symbol scope, schedule, or provider mapping as a repair;
- if the failure is transient, allow the next already-frozen scheduled attempt to run normally;
- if both attempts for the slot are lost, preserve the missing-slot outcome for later V0.11 evaluation.

Any maintenance fix during the frozen window must go through the protected `main` PR path and must not retroactively manufacture evidence for a missed slot.

## Render transport problem

If Render becomes unavailable, unhealthy, suspended, or shows unexpected runtime drift:

- do not switch to V0.2 self-hosted execution;
- do not use Koyeb, Cloudflare Containers, third-party proxies, alternate endpoints, paid tiers, or API-key bypasses;
- do not manually deploy or redeploy Render unless a separate explicit maintenance authority is created and reviewed;
- do not re-enable Auto-Deploy as an emergency fallback;
- record the affected scheduled attempt as failed if capture cannot complete.

Render must never receive R2 credentials.

## Unexpected Render deploy

If the live Render deploy identity changes unexpectedly from the frozen V0.10 activation runtime:

- treat this as intervention-worthy runtime drift;
- do not assume semantic equivalence;
- stop any manual intervention;
- inspect deployment provenance and repository history;
- do not source-switch or continue through an unreviewed alternate runtime path.

The existing scheduled workflow's fail-closed behavior remains authoritative; this runbook does not authorize a replacement runtime.

## Capture artifact boundary anomaly

If the capture artifact indicates any of the following, treat it as intervention-worthy and fail closed:

- object count other than 3 for a PASS result;
- post-write SHA-256 verification not true;
- unexpected provider request count;
- R2 write semantics inconsistent with the frozen receipt contract;
- any R2 delete;
- holdout access;
- `source_switch_authorized` not false;
- `live_trading_authorized` not false;
- capture execution version not `v0_10`.

Do not repair or rewrite the artifact. Preserve it as evidence of the run that occurred.

## Replacement holdout

The replacement holdout remains `FROZEN_UNOPENED` throughout the metadata-capture window.

Do not:

- list holdout objects;
- read holdout candles;
- evaluate holdout outcomes;
- use holdout data to modify metadata thresholds, provider scope, or capture behavior.

Metadata capture and pipeline-health monitoring do not authorize holdout access.

## V0.11 after the full window

After `2026-09-04T01:59:59.999Z`:

- do not immediately list or read production V0.10 R2 receipts;
- first create and merge a separate versioned V0.11 production evaluation execution authority;
- preserve the already-frozen evaluator semantics: exact 194-slot coverage, same-slot duplicate agreement, exact cross-window vector stability, SHA integrity, and fail-closed missing-slot behavior;
- do not read raw provider objects or replacement holdout objects under V0.11 unless separately authorized.

A future metadata-stability PASS still does not authorize replacement holdout access.

## Forbidden interventions summary

During the frozen window, the following remain forbidden without a new explicit versioned authority:

- manual V0.10 production capture or rerun;
- third ad-hoc attempt for an hourly slot;
- retroactive backfill of a missed slot;
- reactivation of V0.2 self-hosted scheduling;
- alternate provider/endpoint/proxy/runtime fallback;
- Render manual deploy/redeploy as an emergency bypass;
- paid cloud upgrade or payment-method fallback;
- deletion or overwrite of frozen evidence to free R2 space;
- V0.11 production R2 evaluation;
- replacement holdout access;
- provider splicing or source switching;
- Trade-Kline W1 materialization;
- strategy changes based on window evidence;
- real-money orders or live trading.

## Operational principle

When an authorized scheduled attempt succeeds, preserve the result. When it fails, preserve the failure. Do not manufacture replacement evidence after the fact.
