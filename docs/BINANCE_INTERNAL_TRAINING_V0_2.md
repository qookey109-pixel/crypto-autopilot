# Binance Internal Training Universe V0.2

This is the historical V0.2 research baseline. Its local-only storage role is
retired and superseded by the R2-only V0.3 pipeline. It is not a deployment
feed, a Pionex replacement, a trade plan, or a live-order surface.

## Scope

- Provider: `binance_spot` public REST API.
- Catalog endpoint: Binance's official public-market-data-only endpoint,
  `https://data-api.binance.vision/api/v3/exchangeInfo`.
- K-lines: `1d`, from `2020-01-01T00:00:00Z` through the latest complete UTC day.
- Default quote assets: `USDT` and `USDC`.
- The catalog retains current `TRADING` markets with spot trading enabled and
  excludes non-ASCII/non-alphanumeric IDs that the parser cannot validate.

The 2026-08-22 local run discovered 748 markets and wrote 701,275 rows through
2026-08-21 UTC. All 748 markets have rows; 723 pass the continuity/price audit
and 25 remain retained with `audit_ok=false` so a future training job can make
an explicit quality decision instead of silently losing history.

## Asset classes

Every row contains `asset_class`, `base_asset`, `quote_asset`, and the
classification method:

- `crypto`: default digital-asset class.
- `stablecoin`: known stablecoin set.
- `other`: known nonstandard assets such as gold-linked or legacy assets.
- `tokenized_stock_candidate`: heuristic candidate, usually a Binance trailing
  `B` symbol. This label is not proof of equity equivalence, ownership,
  settlement, or legal status.

The 2026-08-22 run contains 663 crypto, 13 stablecoin, 8 other, and 64
tokenized-stock-candidate markets. The candidate symbols include examples such
as `AAPLBUSDT`, `AMDBUSDT`, `GOOGLBUSDT`, `MSFTBUSDT`, `NVDABUSDT`, `PLTRBUSDT`,
`QQQBUSDT`, `SPYBUSDT`, and `TSLABUSDT`; their history begins at the exchange
listing date rather than being backfilled to 2020.

## Storage and boundaries

The former ignored local catalog, checkpoints, CSV gzip, Parquet, and receipt
were removed after the corresponding online R2 run passed round-trip SHA-256
verification. New builds may exist only in a GitHub Actions disposable workspace
or a system temporary directory and must be published to R2 for persistence.
The website does not load or display these records. There is no provider splice,
Pionex relabel, holdout access, W1 materialization, trade plan, real-money order,
or live-trading authority.

The online dataset receipt records hashes, counts, audit failures, coverage date,
and all authority flags. Ephemeral per-market checkpoints make public API timeouts
resumable within a run without creating a local persistent archive.
