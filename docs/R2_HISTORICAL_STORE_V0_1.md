# R2 Historical Store V0.1

## Status

**M1B COMPLETE / PAPER-ONLY.**

The storage contract is implemented and has passed real Cloudflare R2 verification with secrets supplied only through GitHub Actions secret management.

Authoritative completion receipt:

`research/receipts/2026-08-18-m1b-r2.json`

Completion evidence includes:

- real R2 upload/download verification;
- frozen M1A bounded dataset materialization in GitHub Actions run `32093154424`;
- 45 Parquet objects / 13,230 total rows / 15 symbols / 3 intervals;
- per-object SHA-256 verified download;
- successful Parquet decode;
- exact candle equality after the R2 round trip;
- dataset manifest and receipt written to R2 and verified.

Observed bounded-dataset Parquet payload: `425,161` bytes.

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

## M1B authority gate

M1B completion requires successful verification of:

1. Parquet encoding.
2. Upload to the real project R2 bucket.
3. Download from R2.
4. SHA-256 equality.
5. Row-count equality.
6. Successful Parquet decode.
7. Exact candle equality against the frozen source dataset.
8. Dataset-level manifest and receipt upload/download verification.

The gate passed for storage run:

`m1b-m1a-upload-32093154424`

R2 manifest:

`manifests/historical/year=2026/month=08/manifest-20260818T024828Z.json`

Manifest SHA-256:

`e0a8252d0853aeaf2f3fbe87e7c1c48d1450eef40140ee399d2c15bcf7ce8d16`

R2 receipt:

`receipts/historical/m1b-m1a-upload-32093154424.json`

Receipt SHA-256:

`846ca4d4f668336b277efe7799a5d46077ee080ec7d0c7dbe81b05fc8cc44cd2`

Required secret environment variables remain:

```text
CLOUDFLARE_ACCOUNT_ID
R2_BUCKET_NAME
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
```

Never commit actual values.

## Next after M1B

1. Measure storage rates from the observed Parquet payload.
2. Estimate one-year and eight-year / approximately 250-market storage and API-operation budgets.
3. Decide which long-horizon intervals remain physical versus deterministic derived/resampled data.
4. Define historical-universe reconstruction to avoid survivorship bias.
5. Build resumable, checkpointed and retry-safe maximum-available acquisition.
6. Begin long-horizon backfill only after capacity and request budgets are reviewed.
