# Qookey Crypto Autopilot — Operations Status 2026-09-14

Status time: `2026-09-14 10:00 Asia/Taipei` (`02:00 UTC`).

Repository `main` remains the formal authority. This document is a read-only operations supplement and grants no execution authority.

## Current reviewed main

- Main: `f6dc32249793c37140ee71fad10603a97f7eeb23`
- PR #294 and PR #295 are merged.
- The exact Binance USD-M lifecycle-gap policy now contains **9 allowances**.
- Policy SHA-256: `97285ba6a66d5d57e2b26f98880bb4450ccd56a9ad5dc9453fded57f86e9bd9e`.
- Policy merge is not data completion.

## Core100 History

Formal Core100 state remains **PARTIAL / 8 of 10**. Full-universe simulation remains **NOT_READY**.

Latest completed scheduled History run observed before the nine-entry policy merge:

- Run: `34792231003`
- Workflow ID: `340899181`
- Event: `schedule`
- Head: `78fed89c94963e67e8ea47bd522d672a4e7966b1`
- Conclusion: `failure`
- Dataset: `IN_PROGRESS`
- Shards complete: `8 / 10`
- Shard index: `8`
- Stage: `DETAILED_HISTORY_SHARD_QUALITY_REJECT`

Latest observed blocker in that run:

- `LITUSDT`
- `2025-12`
- `4h`
- rows: `182`
- gaps: `1`
- missing bars: `4`
- invalid candles: `0`
- misaligned timestamps: `0`
- archive SHA-256: `4d7e61e25eb2fab01e4d1206b36372009ee3bfc60dab72405076e9f6aa8852b2`

The secret-free GitHub artifact for run `34792231003` is `binance-usdm-detailed-history-34792231003-1`, artifact ID `10328099664`, ZIP digest `sha256:095daa2f5d13edd7b4853760b1554d68d801714fa16c0b48cae811741fab92ec`.

Important: run `34792231003` predates the merges of PR #294 and PR #295. It therefore does **not** test the current nine-entry policy. The current production state is `AWAITING_FIRST_SCHEDULED_RUN_ON_NINE_ENTRY_MAIN_OR_DESCENDANT`.

The next nominal History slot is `2026-09-14 10:23 Asia/Taipei`. GitHub scheduled time is not a guaranteed creation time. No manual rerun is authorized by this status review.

## Automation Health

Latest reviewed Health run: `34792852366`.

- Overall: `ALERT`
- Alert count: `1`
- Only alert: Core100 History failure
- Schedule coverage: complete, `7 / 7`
- Training: `HEALTHY_CONDITIONAL`
- Provider/R2/holdout/model-promotion/trade-plan/real-money/live-trading authority assertions: all false

The Health workflow is therefore operating as designed; its red state is not itself an infrastructure failure.

## Training

Latest detailed-training run remains `34750015232`, operationally successful but report state `SKIPPED_DATASET_NOT_READY`.

Next nominal training remains `2026-09-20 12:37 Asia/Taipei`. This status document does not authorize a manual pre-deadline training trigger.

## Safety boundary

Still not authorized:

- source switching
- synthetic or interpolated candles
- direct holdout access
- automatic model promotion
- trade-plan authority
- real-money orders
- live trading
- manual History/R2 rerun from this review

## Next evidence gate

Wait for the first completed `Binance USD-M Crypto Core 100 History V0.1.2` scheduled run on `f6dc32249793c37140ee71fad10603a97f7eeb23` or a legitimate later `main` descendant.

Only then determine whether:

1. the exact CVC/LIT lifecycle allowances are accepted in production;
2. Core100 remains 8/10 with a new fail-closed blocker;
3. a shard may formally advance;
4. or formal 10/10 completion evidence exists.

Workflow success alone is never sufficient to declare data completion.
