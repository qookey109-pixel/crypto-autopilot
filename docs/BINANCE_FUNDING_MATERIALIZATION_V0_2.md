# Binance Funding Materialization V0.2

## Why V0.2 exists

The first full 1,010-source Funding preflight correctly failed before any R2 credentials or writes because the official `HYPEUSDT` June 2026 monthly Funding archive contains one unresolved declared-cadence discontinuity.

Frozen review authority:

`research/receipts/2026-08-19-binance-funding-interior-continuity-review.json`

The observed source rows jump from 2026-06-24 00:00:00.005 UTC to 08:00:00.005 UTC while both adjacent rows declare a 4-hour Funding interval. The expected 04:00 cadence slot is absent from the monthly archive. This is not ordinary millisecond timestamp jitter.

V0.2 therefore reduces materialization scope instead of weakening data-quality rules.

## Exact V0.2 planning scope

- original observed Funding coverage: 1,010 source months;
- deferred annual partition: `HYPEUSDT / 2026`;
- deferred source months: January through July 2026;
- materialized source months: **1,003**;
- annual canonical Parquet objects: **94**;
- annual partition receipts: **94**;
- run metadata objects: **4**;
- total authorized R2 identities after a future authority: **192**.

HYPE remains in the dataset through its complete auditable 2025 May–December partition.

## Frozen V0.2 digests

Canonical 94-partition scope SHA-256:

`1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58`

Canonical 1,003-source checksum-set SHA-256:

`881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3`

The checksum-set digest was recomputed from the already-frozen Funding Coverage artifact using the same canonical line format as V0.1, after excluding only the seven HYPEUSDT 2026 monthly source records.

## Rules that do not change

V0.2 does **not** relax V0.1 safeguards:

- official source checksum required;
- raw `calc_time` preserved exactly;
- source-declared Funding interval preserved exactly;
- long-horizon cadence tolerance remains 50 ms;
- interpolation remains forbidden;
- provider splicing remains forbidden;
- source revisions fail closed;
- existing R2 objects are exact-verify-or-fail, never silently overwritten;
- annual cross-month audit remains mandatory;
- all materialized source archives and all annual builds must PASS before the first R2 write.

## Planning-only boundary

This phase is planning only.

`funding_materialization_authorized=false` and `planning_r2_writes_authorized=false` remain mandatory until a separate V0.2 authority receipt pins the exact scope and checksum-set digests.

Nothing in V0.2 authorizes source switching, Pionex-native relabeling, Historical Universe membership, backtest admission, trade plans, real-money orders or live trading.
