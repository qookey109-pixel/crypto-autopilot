# Qookey Crypto Autopilot — Latest Handoff

Status date: `2026-09-13` (`Asia/Taipei`).

This file is the current navigation entry point. Repository `main`, versioned configs, immutable receipts, and verified GitHub Actions evidence remain authoritative. Re-read latest `main` before every write or merge; never replace newer repository state with this snapshot.

## Current authority baseline

Latest verified `main` at this update:

`d775fbd2ad01834635b8f82391933ac7141e7408`

This is the merge of PR #292, `History: allow exact observed CVC and LIT 1h lifecycle gaps`.

Merge parents were verified exactly:

- previous main: `c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`
- approved PR #292 head: `aa6fe2f268f6e625ce00b33777a6b70fddf4e175`

Operating boundary remains:

- PAPER-ONLY / FREE-ONLY.
- No live trading or real-money orders.
- No formal trade-plan authority.
- No holdout access.
- No source switch or provider relabel.
- No automatic model promotion.
- No synthetic candles, interpolation, forward-fill, or fabricated gap repair.
- No new scheduler or cron authority.
- No manual History/R2 execution merely to accelerate evidence.

## Effective lifecycle-gap policy on main

Policy:

`binance-usdm-lifecycle-gap-v0.1`

Operational classification:

`USER_AUTHORIZED_LIFECYCLE_GAP`

This is an operational treatment only. `causal_claim` remains `NOT_ASSERTED`; lifecycle announcements do not prove the historical cause of every missing timestamp.

Authority receipt on current main:

- config SHA: `863b3eda37c51f33343015cddbe05d0de3b6fd6d75ec8dcef13d190d2e026716`
- exact allowlist entries: 7
- synthetic candles: false
- interpolation: false
- source switch: false
- holdout access: false
- training segmentation required: true

Current exact allowlist:

- CTKUSDT 15m, 2025-04 — SHA `bd77c44d0061511b2e8f5c140a06ad2dd30007c640586fad5b035d71b0c3c61c`, 2,839 rows, 1 gap, 41 missing bars.
- CTKUSDT 1h, 2025-04 — SHA `1fe1c295babc4481dd5c5e9145b68e2bacafe3c6e262528854f8de903ac14b25`, 710 rows, 1 gap, 10 missing bars.
- CTKUSDT 4h, 2025-04 — SHA `08ce76f52b01e9151d64e5df72dca9c5af36ebb41afa9b397edd43fec799862f`, 178 rows, 1 gap, 2 missing bars.
- CVCUSDT 15m, 2025-05 — SHA `d9940880a57d29b57185712e3c12defd2ea5b0f9044d2da23510d9450570bd40`, 2,942 rows, 1 gap, 34 missing bars.
- CVCUSDT 1h, 2025-05 — SHA `236cf0cecf8c927f3f5d07e7fc0c5171a09b60377641b1c7a8df3609674bd454`, 736 rows, 1 gap, 8 missing bars.
- LITUSDT 15m, 2025-12 — SHA `246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160`, 2,906 rows, 1 gap, 70 missing bars.
- LITUSDT 1h, 2025-12 — SHA `8a92afa0f2ee875b880d37161055690394f14172eea48d6e243061db9426c6d3`, 727 rows, 1 gap, 17 missing bars.

Every allowance still requires exact symbol/interval/period, archive SHA, row count, gap count and missing-bar geometry. Duplicate, out-of-order, misaligned or invalid candles fail closed. No unobserved 4h CVC/LIT identity is authorized.

## Training safety remains effective

PR #286 introduced contiguous-segment feature construction before rolling features, returns, targets and labels. Higher-timeframe context cannot reuse stale pre-gap context across a discontinuity.

PR #289 made training revalidate actual materialized R2 candles before feature construction. Ordinary Binance Vision data still requires strict audit; exact lifecycle gaps and checksum/lineage-verified BNX reconciliations pass only through their governed paths. Unknown delivery modes, archive drift, broken repair lineage or new defects fail closed.

## PR #292 — merged and effective

Approved exact head:

`aa6fe2f268f6e625ce00b33777a6b70fddf4e175`

Merge commit / current main:

`d775fbd2ad01834635b8f82391933ac7141e7408`

Merged at `2026-09-13 22:17:05 Asia/Taipei`.

Verified exact-head checks before merge:

- CI `34761917291` — PASS on Python 3.12 and 3.13.
- Dashboard GitHub Pages `34761917282` — PASS.

Verified post-merge checks on `d775fbd2ad01834635b8f82391933ac7141e7408`:

- CI `34762214321` — PASS on Python 3.12 and 3.13.
  - Ruff PASS.
  - Unit tests PASS.
  - R2 cost/budget gate PASS.
  - Observed Binance R2 budget gate PASS.
- V0.10 Critical Path Freeze Guard `34762214349` — PASS.
- Dashboard GitHub Pages `34762214329` — PASS, including build and deploy.
- Dashboard PAPER-ONLY authority assertion — PASS.

PR #292 did not change schedule, trigger History/R2 manually, authorize source switching, synthesize candles, interpolate gaps, open holdout, promote a model, create a trade plan, place orders or authorize live trading.

## Core 100 factual progress

Verified Core100 History status remains **8/10** until a new governed scheduled History report proves otherwise.

Do not claim 9/10 or 10/10 merely because PR #292 is merged.

Before PR #292, protected-main scheduled runs #43–#46 repeatedly observed the two 1h blockers now covered exactly by policy:

### LITUSDT 1h / 2025-12

Runs `34711425773` and `34739234352` both observed:

- SHA `8a92afa0f2ee875b880d37161055690394f14172eea48d6e243061db9426c6d3`
- 727 rows
- 1 gap
- 17 missing bars
- shard index 8
- `shards_complete = 8 / 10`

### CVCUSDT 1h / 2025-05

Runs `34722671256` and `34756244643` both observed:

- SHA `236cf0cecf8c927f3f5d07e7fc0c5171a09b60377641b1c7a8df3609674bd454`
- 736 rows
- 1 gap
- 8 missing bars
- shard index 4
- `shards_complete = 8 / 10`

These are production workflow observations, not inferred archive identities.

## Lifecycle evidence interpretation

CVC official evidence records a prior CVCUSDT perpetual delisting and a May-2025 CVCUSDT perpetual relaunch.

LIT official evidence records ticker identity reuse: the old Litentry LITUSDT perpetual was removed in January 2025, while a distinct Lighter Protocol LITUSDT perpetual launched in December 2025.

These facts support the user's authorized lifecycle-gap operational treatment, but do not prove the lifecycle event caused each missing-timestamp pattern. `causal_claim` remains `NOT_ASSERTED`.

## History cadence

The reviewed schedule remains unchanged:

`23 */2 9-30 9 *`

Operational interpretation in `Asia/Taipei`: every two hours on even local hours at `:23` within the existing September window. GitHub scheduled workflows can be delayed substantially, so API creation time may be much later than the nominal cron slot.

Binding constraints remain:

- one bounded shard per run;
- serialized concurrency;
- FREE-ONLY R2 headroom gates;
- existing recovery/fair-rotation behavior;
- no cadence increase;
- no manual acceleration.

At the moment PR #292 merged, local time was `2026-09-13 22:17:49 Asia/Taipei`; the next nominal History slot was `22:23`. Do not infer its result before a completed scheduled run and artifact exist.

## Automation Health V0.2 interpretation

Recent Automation Health failures are downstream of the latest scheduled Core100 History result being a failure, not evidence of a separate scheduler defect. Do not weaken Health merely to remove the alert. A later successful governed History run should update the monitoring evidence naturally.

## Next bounded operations

Proceed autonomously in this order:

1. Re-read latest `main` before any write.
2. Locate the first completed `Binance USD-M Crypto Core 100 History V0.1.2` scheduled run on `d775fbd2ad01834635b8f82391933ac7141e7408` or a legitimate later main.
3. Verify event, head SHA, jobs, conclusion, artifact and secret-free report.
4. Confirm whether the exact CVC/LIT 1h allowances pass and whether `shards_complete` advances beyond 8.
5. If a new 4h or other discontinuity appears, diagnose only the exact observed symbol/interval/period/SHA/row/gap geometry; do not infer unobserved variants.
6. If another lifecycle-style gap is supported by evidence and falls within the standing user-authorized class, prepare a narrow exact policy PR with tests and receipts, then stop at exact-head merge approval.
7. If Core100 reaches 10/10, verify completion receipts/manifest before changing readiness or training eligibility. Do not create a new training trigger merely to accelerate progress.
8. After the next meaningful scheduled History result, refresh this handoff again before considering this documentation PR for merge.

## Current research readiness

- Full research universe: **NOT_READY**.
- Core100 History: **8/10 last verified**.
- Lifecycle-gap policy: **7 exact entries effective on main**.
- Replacement holdout: **FROZEN_UNOPENED**.
- Automatic model promotion: **NOT_AUTHORIZED**.
- Trade plan: **NOT_AUTHORIZED**.
- Real-money orders / live trading: **NOT_AUTHORIZED**.

## Superseded statements

Older handoffs that say PR #292 is unmerged, that only five lifecycle entries are effective, or that no post-PR #291 scheduled History evidence exists are superseded. Historical receipts should remain immutable; use this file as navigation and re-check repository authority before acting.
