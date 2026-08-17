# R2 Historical Store V0.1

## Status

M1B foundation. The storage contract is implemented, but no Cloudflare bucket is authoritative until a real round-trip proof passes with secrets supplied through a secret manager.

## Cloudflare R2 endpoint

R2 uses the S3-compatible endpoint:

`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

Region is `auto`.

## Capacity target

The layout is designed for up to roughly 250 markets and maximum available history capped at eight years for the research data lake.

Asset families may include:

- crypto core universe
- meme / emerging crypto candidates
- tokenized US-stock / ETF / RWA perpetual instruments

Asset families must remain explicitly classified. Non-crypto instruments must not silently enter a crypto strategy universe.

## Source-of-truth rule

Pionex-native PERP history and any future external proxy history must be stored under separate provenance namespaces. Never splice external spot/equity history into Pionex perpetual history and present it as one native series.

## Object layout

```text
market-data/
  pionex/
    perp/
      BTC_USDT_PERP/
        15m/year=2026/month=08/candles.parquet
        1h/year=2026/candles.parquet
        4h/year=2026/candles.parquet

manifests/historical/year=2026/month=08/manifest-<timestamp>.json
receipts/historical/<run-id>.json
```

Partition policy:

- `15M`: monthly Parquet files
- `60M`: annual Parquet files by default
- `4H`: annual Parquet files by default

A future compaction job may change physical partition sizes only if row counts, timestamps, provenance and SHA-256 receipts remain reproducible.

## Parquet schema

Required columns:

- `time_ms` int64
- `open` float64
- `high` float64
- `low` float64
- `close` float64
- `volume` float64

Compression: Zstandard.

## Provenance contract

Every materialized historical object must be traceable to:

- exchange/provider
- market type
- symbol
- interval
- requested time window
- actual first and last timestamp
- row count
- source request/run identifier
- acquisition timestamp
- SHA-256 of the exact object payload
- audit result for gaps, duplicates and invalid candles

No missing candles are silently interpolated.

## R2 round-trip gate

M1B is not complete until `scripts/r2_roundtrip_proof.py` succeeds against the real project bucket and verifies:

1. Parquet encoding.
2. Upload to R2.
3. Download from R2.
4. SHA-256 equality.
5. Row-count equality.
6. Successful Parquet decode.

Required secret environment variables:

```text
CLOUDFLARE_ACCOUNT_ID
R2_BUCKET_NAME
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
```

Never commit actual values.

## Next after proof

After the real R2 proof passes:

1. Upload the bounded M1A evidence dataset.
2. Verify object-level and dataset-level receipts.
3. Estimate eight-year / 250-market storage and API budgets from observed compression.
4. Begin resumable maximum-available historical backfill.
