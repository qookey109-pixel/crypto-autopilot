# Core100 Fingerprint V0.2 — One-Time Bootstrap Authority Proposal

Status: PROPOSED_NOT_AUTHORIZED  
Evidence basis: main db0acff7d3c493135cae5304d5a1b7b99abc4a63  
Prepared: 2026-09-25 04:12:17 UTC

## Decision requested

The V0.2 comparator and cloud-only evidence collector are prepared but are not active. The current V0.1 weekly workflow remains unchanged. A first V0.2 run has no valid V0.2 predecessor, so the reviewed fail-closed rule returns REVIEW_REQUIRED and does not train or write to R2.

This proposal defines one bounded way to create that first V0.2 baseline. It authorizes nothing by itself. The user must explicitly authorize the one-time baseline training and the exact R2 scope below before a separate activation authority and workflow integration can be merged.

## Recommended isolation

Keep the V0.1 latest pointer and artifacts untouched. Store V0.2 artifacts under:

- `training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2/runs/run=github-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}/` — `model.json`, `metrics.json`, `manifest.json`
- `training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2/latest.json` — V0.2-only latest pointer, written last after output verification

If the V0.2 pointer already exists at bootstrap time, stop with REVIEW_REQUIRED. Never read, migrate, overwrite, or reuse the V0.1 latest pointer as a V0.2 predecessor.

## Proposed one-time execution

Use one explicit `workflow_dispatch` on the existing weekly training workflow after a separately authorized activation receipt and implementation are merged. Do not add a workflow or cron. The dispatch is only the one-time bootstrap; it does not count as natural schedule evidence for the cloud-maintenance acceptance.

Reuse only the already authorized completed Crypto Core 100 dataset contract: 100 crypto USDT perpetual markets, 10 complete shards, 14,274 expected partition objects, intervals 15m/1h/4h, and source months 2022-08 through 2026-07. Require the complete catalog, backfill state, all referenced receipts, and partition SHA-256 checks to agree. Any count, checksum, provider, interval, window, or holdout mismatch stops before training or output writes. Do not make new provider requests.

The dataset identity is SHA-256 over canonical JSON binding the validated catalog key and digest with the 10 shard receipt rows sorted by shard index. Each shard receipt binds its partition object SHA-256 values. Runtime evidence must come from the GitHub-hosted isolated project environment and include the exact Python patch, installed distribution rows, install/build tools, and runner image data when available. Checkout SHA must equal the freshly obtained main SHA.

## Exact proposed R2 scope

Reads:

1. `catalogs/binance_usdm/crypto-core-v0.1/latest.json`.
2. `training/binance_usdm/crypto-core-v0.1/backfill-state.json`.
3. Only the catalog object referenced by the validated catalog pointer.
4. Only the 10 receipt objects referenced by a complete validated backfill state.
5. Only partition objects referenced by those validated receipts, expected maximum 14,274.
6. The new V0.2 latest pointer key to require that no predecessor exists; if present, stop.
7. A fresh, fully paginated whole-bucket `list_objects_v2` inventory of key/size metadata for the project's existing 8,000,000,000-byte FREE-ONLY hard stop. No payloads are read by this headroom listing.

Writes:

1. Exactly one run's `model.json`, `metrics.json`, and `manifest.json` under the V0.2 run prefix above. Require the existing hard-stop/headroom gate, exact immutable-object equality, and SHA-256 readback.
2. Write the V0.2 `latest.json` pointer last, after all immutable objects verify. The V0.1 pointer remains unchanged.

If GitHub, R2, or any evidence is incomplete; if the headroom inventory is incomplete; if the hard stop is reached; or if the V0.2 pointer unexpectedly exists, stop without fallback. No automatic retraining is authorized after this one-time bootstrap. A later dataset/runtime/guard change returns REVIEW_REQUIRED until a new authority is merged.

## Unchanged boundaries

The existing quality result is recorded as evidence; it does not promote a model. This proposal authorizes no holdout, provider request, source switch, R2 namespace outside the exact scope, live trading, real-money orders, new secrets, paid runtime, or schedule change. Budget remains 0 USD/month.

## Required authority gate

Before code is wired into the active workflow, a successor versioned authority and receipt must record the user's decision, exact object/key scope, exact bootstrap count, FREE-ONLY gate, and stop/rollback behavior, and be merged to main. Then implementation CI must pass on Python 3.12/3.13; the production workflow remains on its currently requested Python version unless separately reviewed. Only after that may the one explicit dispatch occur.

**The present proposal remains non-authorizing.**
