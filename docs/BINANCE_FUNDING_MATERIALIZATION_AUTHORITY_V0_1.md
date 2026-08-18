# Binance Funding R2 Materialization Authority V0.1

## Purpose

Define the exact scope and fail-closed writer contract that may later be granted explicit permission to materialize the already-frozen Binance Funding coverage into provider-separated Cloudflare R2 storage.

This planning phase is read-only. It does **not** authorize or perform R2 writes.

## Prerequisite authorities

- Funding Source Proof: `research/receipts/2026-08-18-binance-funding-source-proof.json`
- Funding Coverage: `research/receipts/2026-08-18-binance-funding-coverage.json`
- Funding R2 Budget: `research/receipts/2026-08-18-binance-funding-r2-budget.json`

The budget authority must be `PASS / NO_MATERIAL_BUDGET_CHANGE` before an explicit materialization authority can be proposed.

## Exact scope

The materialization scope is derived only from the frozen Funding Coverage authority:

- 15 Binance USD-M symbols;
- 1,010 checksum-observed monthly Funding archives;
- 95 symbol-year canonical partitions;
- annual canonical key:
  `market-data/binance_usdm/perp/{SYMBOL}/funding/year={YYYY}/funding.parquet`;
- one provider-separated partition receipt per canonical object.

No month before a symbol's observed Funding boundary is added. No current incomplete August 2026 month is added.

The planner emits a canonical SHA-256 over the exact ordered annual symbol/year/month scope. The eventual authority receipt and writer must pin that digest.

## Preflight-before-write contract

The V0.1 writer must not perform the first R2 write until **all** of the following have completed successfully for the entire authorized 1,010-month scope:

1. Every monthly Funding archive and `.CHECKSUM` is fetched.
2. Every archive SHA matches the official checksum.
3. Every archive passes the frozen Funding ZIP/schema audit.
4. Raw `calc_time` timestamps remain unique and strictly increasing.
5. Source-declared `funding_interval_hours` is preserved.
6. Monthly cadence residuals pass the explicitly authorized 50 ms long-horizon materialization audit tolerance.
7. Each symbol-year aggregation passes cross-month uniqueness/order/cadence audit.
8. Every annual Zstd Parquet artifact is built locally.
9. The complete local manifest is frozen before writes begin.

A failure in any source month or annual partition therefore causes **zero new R2 writes** for that run.

## Existing-object policy

V0.1 never blindly overwrites an existing Funding object.

For an existing canonical object or partition receipt:

- exact byte/SHA equality -> verify and reuse;
- any mismatch -> fail closed and require explicit revision review.

This preserves idempotence and prevents source revisions from silently changing historical research data.

## Planned R2 operation shape

The frozen exact scope contains:

- 95 canonical annual Funding Parquet objects;
- 95 annual partition receipts;
- 4 run-level metadata objects;
- 194 planned R2 writes total.

The no-material-change budget authority already stress-tested this operation shape and the conservative one-hour row upper bound.

## Authority separation

The eventual explicit authority may authorize only:

- Binance Funding R2 writes for the exact pinned scope;
- canonical annual Funding Parquet objects;
- partition receipts;
- run-level Funding materialization metadata.

It must **not** authorize:

- Binance -> Pionex source substitution;
- provider splicing;
- Pionex-native relabeling;
- Historical Universe membership;
- backtest admission;
- strategy-parameter changes;
- automatic trade plans;
- real-money orders;
- live trading.

Funding materialization is therefore a storage/evidence step only.

## After explicit authority

Only a separately frozen receipt that pins the exact materialization-scope SHA and flips Funding-specific R2-write permission may unlock the writer.

The writer must verify that receipt at runtime before it can access the R2 write path.
