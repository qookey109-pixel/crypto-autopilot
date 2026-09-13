# Qookey Crypto Autopilot — Latest Handoff

Status date: `2026-09-13` (`Asia/Taipei`).

This file is the current navigation entry point. Repository `main`, versioned configs, immutable receipts, and verified GitHub Actions evidence remain authoritative. Re-read latest `main` before every write or merge; never replace newer repository state with this snapshot.

## Current authority baseline

Latest verified `main` at this update:

`c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`

This is the merge of PR #291, `History: allow exact CVC lifecycle gap`.

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

The effective `main` allowlist currently contains five exact archive identities:

- CTKUSDT 15m, 2025-04 — SHA `bd77c44d0061511b2e8f5c140a06ad2dd30007c640586fad5b035d71b0c3c61c`, 2,839 rows, 1 gap, 41 missing bars.
- CTKUSDT 1h, 2025-04 — SHA `1fe1c295babc4481dd5c5e9145b68e2bacafe3c6e262528854f8de903ac14b25`, 710 rows, 1 gap, 10 missing bars.
- CTKUSDT 4h, 2025-04 — SHA `08ce76f52b01e9151d64e5df72dca9c5af36ebb41afa9b397edd43fec799862f`, 178 rows, 1 gap, 2 missing bars.
- CVCUSDT 15m, 2025-05 — SHA `d9940880a57d29b57185712e3c12defd2ea5b0f9044d2da23510d9450570bd40`, 2,942 rows, 1 gap, 34 missing bars.
- LITUSDT 15m, 2025-12 — SHA `246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160`, 2,906 rows, 1 gap, 70 missing bars.

Exact symbol/interval/period, archive SHA, row count, gap count and missing-bar geometry must match. Duplicate, out-of-order, misaligned or invalid candles still fail closed. CTK entries additionally pin exact gap boundaries where verified.

## Training safety remains effective

PR #286 introduced contiguous-segment feature construction before rolling features, returns, targets and labels. Higher-timeframe context is prevented from reusing stale pre-gap context across a discontinuity.

PR #289 made training revalidate actual materialized R2 candles before feature construction. Ordinary Binance Vision data still requires strict audit; lifecycle gaps and BNX repaired partitions pass only through their exact governed paths. Unknown delivery modes, archive drift, broken repair lineage or new defects fail closed.

Verified PR #289 merge baseline:

`b4adddad2c5c14aed2c01338b075a323d846653d`

Post-merge checks were PASS:

- CI `34697230836`.
- V0.10 Critical Path Freeze Guard `34697230876`.

## PR #291 — CVC 15m now effective

Approved exact head:

`cdb2cf1d98444bd6f49c8e7830027d5a6b3d52d7`

Merge/main:

`c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`

Verified post-merge checks:

- V0.10 Critical Path Freeze Guard `34703745490` — PASS.
- CI `34703744679` — PASS.
- Dashboard GitHub Pages `34703744618` — PASS.

PR #291 did not authorize any generic gap bypass. It added only the production-observed CVCUSDT 15m May-2025 identity.

## Core 100 factual progress

Verified Core100 History status remains **8/10**.

Do not claim 9/10 or 10/10 until a governed History report shows the corresponding `shards_complete`, receipt publication and R2 state advancement.

After PR #291, protected-main scheduled History runs did execute on `c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`. They proved that the 15m allowance was no longer the terminal blocker, but surfaced exact 1h discontinuities:

### Scheduled run #43

Run `34711425773`:

- event: `schedule`
- head: `c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`
- status: FAIL / `DETAILED_HISTORY_SHARD_QUALITY_REJECT`
- shard index: 8
- `shards_complete`: 8 / 10
- symbol: LITUSDT
- interval: 1h
- period: 2025-12
- archive SHA: `8a92afa0f2ee875b880d37161055690394f14172eea48d6e243061db9426c6d3`
- rows: 727
- gap count: 1
- missing bars: 17
- invalid candles: 0
- misaligned timestamps: 0

### Scheduled run #44

Run `34722671256`:

- event: `schedule`
- head: `c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`
- status: FAIL / `DETAILED_HISTORY_SHARD_QUALITY_REJECT`
- shard index: 4
- `shards_complete`: 8 / 10
- symbol: CVCUSDT
- interval: 1h
- period: 2025-05
- archive SHA: `236cf0cecf8c927f3f5d07e7fc0c5171a09b60377641b1c7a8df3609674bd454`
- rows: 736
- gap count: 1
- missing bars: 8
- invalid candles: 0
- misaligned timestamps: 0

### Scheduled run #45

Run `34739234352` repeated the same LITUSDT 1h exact blocker as run #43:

- archive SHA `8a92afa0f2ee875b880d37161055690394f14172eea48d6e243061db9426c6d3`
- 727 rows
- 1 gap
- 17 missing bars
- shard index 8
- `shards_complete`: 8 / 10

This repetition is production evidence, not an inferred archive identity.

## LIT ticker lifecycle evidence

Binance official announcements show two distinct LITUSDT perpetual identities across 2025:

- The Litentry (LIT) USDⓈ-M perpetual was automatically settled and removed at `2025-01-31 09:00 UTC` as part of the Litentry-to-Heima rebrand.
- A distinct Lighter Protocol (LIT) LITUSDT perpetual pre-market contract launched at `2025-12-23 17:30 UTC`.

This confirms a ticker lifecycle / identity reuse exists. It does **not** prove that this lifecycle caused the exact Binance Vision archive discontinuity, so `causal_claim` remains `NOT_ASSERTED`.

## PR #292 — prepared, CI green, not merged

Open PR:

`#292 — History: allow exact observed CVC and LIT 1h lifecycle gaps`

Branch:

`codex/lifecycle-gap-1h-v0-1-20260913`

Exact reviewed head at this handoff:

`6427a3318fdb370b5489661fb2835f180e8ac44a`

Base:

`c7990a63b7d8f21aae12ff13b51e9d0ee5189fab`

PR #292 adds only the two production-observed 1h identities above. It does **not** guess or authorize 4h variants.

Policy config SHA proposed by PR #292:

`863b3eda37c51f33343015cddbe05d0de3b6fd6d75ec8dcef13d190d2e026716`

Proposed exact allowlist size after merge: 7 entries.

Verified exact-head checks:

- CI run `34761747284` — PASS on Python 3.12 and 3.13.
  - Ruff PASS.
  - Unit tests PASS.
  - R2 cost/budget gate PASS.
  - Observed Binance R2 budget gate PASS.
- Dashboard GitHub Pages run `34761747286` — build PASS; PR deploy intentionally skipped.
- PR is mergeable.

PR #292 must **not** be merged without explicit user approval of exact head `6427a3318fdb370b5489661fb2835f180e8ac44a` after a final main/head recheck.

## Automation Health V0.2 interpretation

Recent Automation Health failures are not a second independent defect. The health checker reports an alert because the latest accepted scheduled Core100 History run is a failure. Schedule coverage and authority guards remain intact.

Do not weaken Health merely to remove the alert. Once a newer scheduled History run succeeds, Health should naturally reflect that newer workflow evidence.

## History cadence

Existing reviewed cadence remains unchanged:

`23 */2 9-30 9 *`

Operational interpretation in `Asia/Taipei`: every two hours on even local hours at `:23` within the existing September execution window. GitHub scheduled workflows may start late.

Binding constraints remain:

- one bounded shard per run;
- serialized concurrency;
- FREE-ONLY R2 headroom gates;
- existing recovery/fair-rotation behavior;
- no cadence increase from lifecycle handling.

## Next bounded operations

Proceed autonomously in this order:

1. Re-read latest `main` and PR #292 immediately before any merge decision.
2. Verify PR #292 head is still exactly `6427a3318fdb370b5489661fb2835f180e8ac44a` and its exact-head checks remain PASS.
3. Merge PR #292 only after explicit approval of that exact head.
4. Verify the resulting `main`, merge parents, post-merge CI, Freeze Guard and Dashboard Pages.
5. Do not manually trigger History/R2. Wait for the existing scheduled History cadence.
6. Inspect the next completed scheduled History artifact/report. Determine whether CVC/LIT 1h exact allowances pass and whether `shards_complete` legitimately advances beyond 8.
7. If a 4h or other new discontinuity appears, diagnose only the exact observed symbol/interval/period/SHA/geometry. Do not infer or pre-authorize unobserved intervals.
8. If Core100 reaches 10/10, verify completion receipts/manifest before changing readiness. The existing training schedule/gate remains authoritative; do not create a new training trigger merely to accelerate progress.

## Current research readiness

- Full research universe: **NOT_READY**.
- Core100 History: **8/10 last verified**.
- PR #292: **READY FOR EXACT-HEAD APPROVAL; NOT MERGED**.
- Replacement holdout: **FROZEN_UNOPENED**.
- Automatic model promotion: **NOT_AUTHORIZED**.
- Trade plan: **NOT_AUTHORIZED**.
- Real-money orders / live trading: **NOT_AUTHORIZED**.

## Superseded statements

Older handoffs that say no post-PR #289/291 scheduled History run existed are now superseded. Historical receipts should remain immutable; use this file as navigation and re-check repository authority before acting.
