# Binance Funding R2 Materializer V0.1

## Purpose

Materialize the already-authorized Binance USD-M Funding history into provider-separated Cloudflare R2 annual Parquet partitions without changing provider provenance or unlocking trading.

## Frozen authorities

The writer requires all of the following Repository authorities to PASS before it can enter the write path:

- `research/receipts/2026-08-18-binance-funding-materialization-authority.json`
- `research/receipts/2026-08-18-binance-funding-materialization-authority-amendment.json`
- `research/receipts/2026-08-18-binance-funding-source-checksum-set.json`
- `research/receipts/2026-08-18-binance-funding-coverage.json`

The exact materialization scope is pinned by:

- canonical scope SHA-256: `81f64c4f07f1c77bf8391962e0ff7b3eb5f004d4a53bd0d9b8f50328c18c267c`
- source checksum-set SHA-256: `7ed43292ecee61c358360b8a255fb7e7844bf7ac10626425c44292b4ad92963a`
- 15 Binance USD-M symbols
- 1,010 monthly source archives
- 95 annual canonical Funding Parquet objects
- 95 annual partition receipts
- 4 run-level metadata objects

## Full preflight before first write

The writer performs the complete preflight before creating the R2 write plan:

1. Rebuild the exact 95-partition scope from the frozen Funding Coverage authority.
2. Validate the storage-only materialization authority and checksum-set-bound amendment.
3. Fetch all 1,010 official Binance Vision `.CHECKSUM` files.
4. Recompute the ordered checksum-set digest and require exact equality with the frozen digest.
5. Fetch all 1,010 monthly Funding ZIP archives.
6. Verify every official checksum, ZIP member, CSV schema, timestamp uniqueness/order and source-declared Funding interval.
7. Apply the frozen 50 ms long-horizon cadence-jitter tolerance without rounding or changing any source timestamp.
8. Build all 95 annual symbol/year aggregates and cross-month cadence-audit them.
9. Build all 95 Zstd Parquet payloads locally.
10. Freeze source manifest, canonical manifest and preflight receipt before the first R2 write.

Any source/checksum/scope/content/annual-build failure therefore produces zero new R2 writes.

## PR preflight workflow

`.github/workflows/binance-funding-r2-preflight.yml` runs on writer-related pull requests and on manual dispatch.

It has no R2 credentials and executes only:

```text
scripts/materialize_binance_funding_r2.py --mode preflight
```

A PASS from this workflow proves the implementation can reconstruct and audit the complete authorized source scope at that execution time. It does not perform storage writes.

## Execution marker

The R2 workflow requires:

`config/binance_funding_r2_materialization_execution_v0_1.json`

The marker is intentionally not part of the writer implementation PR. It must explicitly pin the same scope SHA, checksum-set SHA and three authority paths, while keeping source switch, Pionex-native relabeling, backtest admission, trade plans and live trading false.

Without that marker, the materialization workflow cannot enter the writer.

## R2 conflict scan before first write

After the full source/local preflight, write mode creates the R2 client and performs an exact prewrite scan across all 194 authorized object identities.

For an existing object:

- exact bytes -> verify/reuse;
- any byte mismatch -> fail closed before new writes start.

This includes the 95 annual canonical objects, 95 annual partition receipts and 4 run-level metadata objects.

## Write order and idempotence

The writer addresses exactly 194 authorized identities for one run:

1. source manifest;
2. canonical manifest;
3. preflight receipt;
4. 95 canonical annual Funding objects and 95 matching partition receipts;
5. final result receipt.

Canonical/partition-receipt objects are deterministic. Run metadata is keyed by GitHub run id and uses deterministic payloads for that run id. A re-run can therefore exact-verify/reuse previously completed objects; mismatches are never overwritten.

A network failure after writes begin can leave a partial set of exact authorized objects. A later rerun is expected to verify/reuse those exact objects and continue. The writer never treats a partial run as PASS because the final result object is written only after all prior objects have been verified.

## Post-write verification

Every canonical Parquet object is downloaded/verified after upload or reuse and decoded back into Funding observations. Exact observation equality is required against the locally preflighted source aggregate.

Partition receipts preserve:

- provider `binance_usdm`;
- source months and monthly archive SHA-256 values;
- annual row count and first/last source timestamps;
- source-declared Funding interval values;
- canonical Parquet SHA-256 and byte count;
- the frozen scope and source-checksum-set digests.

## Explicitly not authorized

This materializer does not authorize or implement:

- Binance -> Pionex source substitution;
- provider splicing;
- Pionex-native relabeling;
- Historical Universe membership;
- backtest admission;
- strategy parameter changes;
- automatic trade plans;
- private Pionex API calls;
- real-money orders;
- live trading;
- Trade-Kline W1 materialization;
- Mark Price materialization;
- Open Interest materialization.

It is a historical storage/evidence component only.
