# Binance Funding R2 Materializer V0.2

## Purpose

Implement the writer-side preflight contract for the already-authorized Funding V0.2 storage scope without performing any R2 write in the implementation PR.

Authority:

`research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json`

## Exact V0.2 scope

- provider: `binance_usdm`
- delivery: `binance_vision`
- dataset: `fundingRate`
- 1,003 monthly source archives
- 94 annual canonical Funding Parquet objects
- 94 annual partition receipts
- 4 future run metadata objects
- 192 future R2 identities
- HYPEUSDT 2026 annual partition deferred

Canonical scope SHA-256:

`1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58`

Source checksum-set SHA-256:

`881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3`

## PR full preflight

The PR workflow receives no R2 or exchange credentials and performs:

1. rebuild the exact V0.2 annual scope from frozen Coverage evidence;
2. validate the V0.2 storage-only runtime authority;
3. enumerate exactly 1,003 monthly Binance Vision Funding source identities;
4. fetch all 1,003 official `.CHECKSUM` files and ZIP archives;
5. verify checksum filename and SHA-256 for every archive;
6. parse and audit every archive with the frozen 50 ms long-horizon cadence tolerance;
7. recompute the canonical 1,003-source checksum-set digest;
8. require exact equality with the V0.2 authorized checksum-set digest;
9. aggregate all 94 annual symbol/year partitions;
10. run cross-month order / uniqueness / cadence audits;
11. build all 94 annual Zstd Parquet payloads locally;
12. decode every local Parquet payload back to Funding observations and require exact observation equality.

Any failure keeps the writer PR blocked.

## No write boundary

The preflight implementation does not import or construct the R2 storage client and explicitly records:

- `r2_credentials_used=false`
- `r2_client_constructed=false`
- `r2_writes_performed=false`

A successful preflight proves the exact authorized source scope can be reconstructed and serialized at that execution time. It does not prove that R2 materialization has occurred.

## Deferred HYPE scope

`HYPEUSDT / 2026` is absent from all V0.2 writer source keys and annual builds. Its source gap must not be repaired by:

- interpolation;
- copying a neighboring Funding rate;
- provider splicing;
- source switching.

HYPEUSDT 2025 May–December remains in the authorized materialized scope.

## Still not authorized

This writer phase does not authorize:

- source switching;
- provider splicing;
- Pionex-native relabeling;
- Historical Universe membership;
- backtest admission;
- strategy parameter changes;
- automatic trade plans;
- private Pionex API usage;
- real-money orders;
- live trading.

Only after a full V0.2 preflight PASS may a separately reviewed execution step construct the R2 client and perform the exact 192-identity storage materialization contract.
