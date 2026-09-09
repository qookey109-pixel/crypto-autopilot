# BNX Archive Repair V0.1

Status: AUTHORIZED ONLY AFTER REVIEWED MAIN MERGE.
This appendix does not claim a production repair has already happened.

## Evidence and exact scope

GitHub diagnosis [34241295251](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34241295251)
ran on main commit 468628c96c980980c4637823ff9e6eca207f0f60.
It found 288 missing BNXUSDT 15m candles in August 2022, supplied by official
August 10, 11 and 12 daily archives. August 1 supplies 96 exact overlapping rows.
The complete 2976-row normalized candidate SHA-256 is
24d441889b173fa85205b189c8c63d316eac34461a29476f618a640b079f26ad.

Config: config/bnx_archive_repair_v0_1.json
SHA-256: 08721e700471fa2a66b686733d21e531ee9216d5607d4a5080d9c2846e985cdd
Receipt: research/receipts/2026-09-09-bnx-archive-repair-v0-1-authority.json

The original monthly ZIP and each of four daily ZIP hashes are pinned in the
config. Checksum validation, exact overlap, full UTC-month audit, exact counts
and normalized candidate hash must all pass again before materialization.
No interpolation, monthly source regrading, substitution of another provider,
or extrapolation to 1h/4h or any other month/market is permitted.

## Single execution path

The existing Crypto Core history workflow receives this optional appendix.
Its six-hour cron, concurrency group, original config, recovery fairness and
128-attempt recovery budget remain unchanged. After merge, normal scheduled
runs can use the appendix when fair shard rotation reaches BNX. A fresh manual
main run is also allowed; it may not override fair rotation. Rerun attempts,
push/PR execution, local execution and simulated CLI clocks are rejected before
constructing R2. The appendix requires the existing recovery contract.

No extra workflow, manual publication lane or secret binding is added.
The diagnosis-only job retains zero R2 access and is unchanged.
The execution deadline remains exclusive 2026-10-01T00:00:00Z, using the real
clock at entry, before each reconstruction request and before repair writes.
At most ten public requests are made per reconstruction: one monthly and four
daily ZIP/checksum pairs, through the already bounded no-retry/no-redirect
reader. Maximum response is 8 MB, total 20 MB; no API key or fallback is used.

## Publication and immutable evidence

Only the exact missing original partition key named by the config may be
created. If an existing partition contains different candles (or cannot be
decoded), fail with no replacement. Equal existing candles are verified and
reused. This is safe recovery, not an overwrite authorization.

The whole shard still validates before writes. The existing whole-bucket
metadata-only FREE-ONLY 8 GB headroom checks remain required before provider
access and writing; repair additionally checks the real clock and fresh
headroom at the repaired object, shard receipt and completion-pointer gates.
Bucket inventory is for byte accounting only, not holdout/raw content access.
Use the existing serialized writer, original Parquet representation and exact
SHA readback; do not introduce a second R2 adapter or new storage service.

The shard object record explicitly labels monthly/daily reconciliation:
original monthly row count 2688 and original audit false remain visible;
source_rows 2976 is the reconstructed partition count. An embedded repair
lineage records all five source hashes, candidate hash, 288 insertions, 96
overlaps, config hash and original diagnostic run. R2 object metadata also
identifies the repair config and candidate. The original monthly archive
receipt is not fabricated or marked PASS.

Write the immutable shard receipt after object readback, then the existing
completion pointer last. A failed run cannot complete a shard. Interrupted
writes can be resumed only under the same exact candidate and original
equality checks. If another partition fails, the entire shard remains
incomplete. All ten original shards remain necessary for dataset completion;
this one repair does not authorize partial-data training or assert completion.

## Boundaries and review

The diagnosis config/receipt and original Crypto Core and recovery authorities
remain byte-for-byte unchanged. This new versioned appendix alone proposes the
bounded daily-input and missing-partition creation permission.
No holdout, frozen metadata-path change, source switch, Pionex-native relabel,
strategy/risk/leverage change, model promotion, trade plan, paper activation or
real-money order is granted. Raw candles stay in R2, never Pages/artifacts.
The website remains a derived view.

Cloud CI uses synthetic archives and an in-memory store, not production R2.
Production execution must be verified with run evidence after human merge
review. Other missing partitions require new evidence and a separate decision.
