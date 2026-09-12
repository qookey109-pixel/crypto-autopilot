# Qookey Crypto Autopilot — Latest Handoff

Status date: `2026-09-12` (`Asia/Taipei`).

This file is the current handoff entry point. Repository `main`, versioned configs, immutable receipts, and verified GitHub Actions evidence remain authoritative. Older handoffs and `PROJECT_STATUS.md` sections remain historical evidence and may contain superseded present-tense statements.

## Current authority baseline

Base authority immediately before this documentation update:

`b4adddad2c5c14aed2c01338b075a323d846653d`

That commit is the merge of PR #289. Before any future write or merge, re-read latest `main`; never replace newer repository state with this pinned snapshot.

Current operating boundary remains:

- PAPER-ONLY / FREE-ONLY.
- No live trading or real-money orders.
- No formal trade-plan authority.
- No holdout access.
- No source switch or provider relabel.
- No automatic model promotion.
- No synthetic candles, interpolation, forward-fill, or fabricated gap repair.
- No new scheduler or cron authority is created by this handoff.

## Lifecycle-gap decision now effective

PR #288, `History: allow exact lifecycle gaps without synthetic candles`, was merged from approved exact head:

`5302bf9107c75ea5acb2f33a154204fdde107bb8`

The effective policy is `binance-usdm-lifecycle-gap-v0.1`.

It permits only checksum- and geometry-pinned reviewed lifecycle-style gaps to be treated operationally as:

`USER_AUTHORIZED_LIFECYCLE_GAP`

This is an operational classification, not a historical claim that delisting caused every gap.

The allowlist is limited to:

- CTKUSDT 15m, 2025-04 — archive SHA `bd77c44d0061511b2e8f5c140a06ad2dd30007c640586fad5b035d71b0c3c61c`, 2,839 rows, 1 gap, 41 missing bars.
- CTKUSDT 1h, 2025-04 — archive SHA `1fe1c295babc4481dd5c5e9145b68e2bacafe3c6e262528854f8de903ac14b25`, 710 rows, 1 gap, 10 missing bars.
- CTKUSDT 4h, 2025-04 — archive SHA `08ce76f52b01e9151d64e5df72dca9c5af36ebb41afa9b397edd43fec799862f`, 178 rows, 1 gap, 2 missing bars.
- LITUSDT 15m, 2025-12 — archive SHA `246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160`, 2,906 rows, 1 gap, 70 missing bars.

Exact archive SHA, identity, row count, gap count, and missing-bar geometry are required. Unknown gaps, changed archives, duplicate/out-of-order rows, misalignment, or invalid candles remain fail-closed.

## Training path now effective

PR #289, `Training: revalidate lifecycle gaps and repaired partitions`, was merged from approved exact head:

`13cb0e1a153ffcabf0d1f477d0e3fb28c14fe147`

Merge commit / baseline main:

`b4adddad2c5c14aed2c01338b075a323d846653d`

Verified PR CI: run `34696945014` — PASS.

Verified post-merge main checks:

- CI run `34697230836` — PASS.
- V0.10 Critical Path Freeze Guard run `34697230876` — PASS.

Training now revalidates actual materialized R2 candles before feature construction:

- Ordinary Binance Vision partitions still require a fresh strict candle audit.
- CTK/LIT non-contiguous partitions are accepted only when actual candles plus source archive SHA reproduce the exact lifecycle allowlist entry.
- BNX monthly/daily reconciliation partitions are accepted only when restored Parquet is contiguous and immutable repair lineage plus recomputed candidate SHA agree.
- Unknown delivery modes, new gaps, archive-SHA drift, row-count drift, broken repair lineage, invalid candles, or misalignment remain fail-closed.

The existing segmentation layer remains required, so rolling lookbacks, returns, targets, labels, and higher-timeframe context may not bridge a discontinuity.

## Core 100 factual progress

Keep the verified dataset status at **8/10** until a real production/history workflow proves otherwise.

Do not infer 9/10 or 10/10 merely because PR #288 and PR #289 are merged.

The history writer marks a shard complete only after the governed shard receipt is published and the serialized R2 state pointer is updated. Dataset `COMPLETE` requires all ten distinct governed shards.

As of the latest check around `2026-09-12 22:32 Asia/Taipei`, the expected new scheduled Core 100 History run for the current lifecycle policy had not yet appeared in the GitHub Actions schedule listing. The latest visible scheduled History run remained the earlier failed run `34693135969` on older main `fd656b6c4d5bd4ee47cecdc6781f66c992a48bcf`.

Absence of a new run is not a failure conclusion. GitHub scheduled workflows may start late. Do not add a second scheduler or manually accelerate the bounded cadence merely to manufacture progress evidence.

## History cadence

Existing reviewed cadence remains unchanged:

`23 */2 9-30 9 *`

Operational interpretation in `Asia/Taipei`: every two hours on even local hours at `:23`, through the existing September execution window.

Binding constraints remain:

- one bounded shard per run;
- serialized concurrency;
- FREE-ONLY R2 headroom gates;
- existing recovery/attempt limits;
- no cadence increase from this handoff.

## Downstream gate audit

The post-PR audit found no additional lifecycle-gap blocker in the following layers:

### History completion

Backfill completion is based on ten distinct PASS shard receipts and the R2 backfill state. It does not require every source object's `audit_ok` to be true after the exact lifecycle policy has admitted the source archive.

### Training

Handled by PR #289 through fresh materialized-data revalidation and exact policy/repair checks.

### Automation Health V0.2

Automation Health reads GitHub workflow metadata such as event, conclusion, and age. It does not inspect R2 candle `audit_ok`, so no lifecycle-specific code change is required there.

Until a newer successful History run exists, Automation Health may continue to report history unhealthy because its latest accepted scheduled history evidence is a failure. That is an expected monitoring result, not a new code defect.

### Dashboard cloud-run projection

`build_cloud_run_status.py` deliberately does not convert workflow success into dataset-completion authority; `datasetComplete` remains unasserted. The dashboard should therefore remain evidence-driven rather than promote 8/10 to complete based only on workflow metadata.

## Superseded present-tense statements

Older 2026-09-12 documents contain statements that were correct when written but are no longer current, including:

- CTK lifecycle exception “not authorized”.
- The next task being to design lifecycle exception + segmentation.
- PR #284 / older main being the latest baseline.
- CTK/LIT quality gaps being unconditional whole-pool blockers.

Do not delete or rewrite those historical snapshots. This file supersedes them for current navigation while preserving their evidence value.

## Next bounded operations

Proceed autonomously in this order:

1. Re-read latest `main`.
2. Inspect the first new `Binance USD-M Crypto Core 100 History V0.1.2` scheduled run after PR #288/#289.
3. Verify its event, exact head SHA, jobs, conclusion, and secret-free report artifact.
4. Confirm whether CTK/LIT exact lifecycle gaps were accepted and which shard advanced.
5. Read the report's `shards_complete`, `shard_count`, and `dataset_status`; never infer these from workflow success alone.
6. If the run reveals a new unknown archive/gap/lineage condition, preserve fail-closed behavior and diagnose it before proposing any new exception.
7. If the dataset actually reaches COMPLETE, then verify the existing weekly/manual training gate against the same R2 state before updating readiness/dashboard docs.

No merge should be performed without explicit approval of that PR's exact head SHA.

## Current research readiness

- Full research universe: **NOT_READY**.
- Fixed BTC 27-day simulation: scoped historical sample PASS / engine validation only.
- Pionex candidate counts are selection evidence, not materialized full-history evidence.
- Core 100 History: **8/10 last verified**, pending new scheduled evidence.
- Replacement holdout: **FROZEN_UNOPENED**.
- Live trading: **NOT_AUTHORIZED**.
