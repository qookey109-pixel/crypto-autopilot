# Binance 2025 R2 Pilot V0.1

Updated: 2026-08-18

## Purpose

Materialize the first content-audited 15-market Binance USD-M year-scale dataset into Cloudflare R2 while preserving the provider boundary established by the earlier Binance Vision proofs.

This pilot is research/backtest-only. Pionex remains the execution-target exchange.

## Input authority

The pilot consumes:

`research/receipts/2026-08-18-binance-2025-coverage-scan.json`

That authority froze checksum-backed archive presence for the M1A 15-market candidate list:

- 14 Binance symbols have all 12 months of 2025 archive presence for `15m`, `1h`, `4h`;
- HYPEUSDT has archive presence only for 2025-05 through 2025-12;
- archive presence alone was explicitly not treated as candle completeness.

## Content proof

For every expected monthly Binance Vision Kline archive, this pilot downloads:

1. the official ZIP;
2. the official `.CHECKSUM`;
3. verifies ZIP SHA-256;
4. verifies the expected CSV member;
5. parses every row;
6. requires strict candle audit with no duplicates/gaps/interpolation;
7. requires exact month-end coverage;
8. requires exact month-start coverage except HYPEUSDT's first available month, where a provider-native partial start is allowed and recorded.

For HYPEUSDT, no synthetic January-April data is created.

## R2 partition policy

Trade Klines only in this pilot:

- `15M`: monthly canonical objects;
- `60M`: annual canonical object assembled from audited monthly `1h` archives;
- `4H`: annual canonical object assembled from audited monthly `4h` archives.

Expected canonical object count: **206**.

The annual `60M` and `4H` objects must pass a second cross-month candle audit after concatenation. This prevents a missing month boundary from being hidden by individually valid monthly archives.

## Provider namespace

All canonical keys must begin with:

```text
market-data/binance_usdm/
```

The pilot fails if any Binance object attempts to use:

```text
market-data/pionex/
```

An existing Binance canonical object is never overwritten. It is accepted only if the decoded existing Parquet candles exactly equal the current frozen source candles.

## R2 verification

Each partition:

1. converts to the existing Zstd Parquet candle schema;
2. uploads or verifies an existing canonical object;
3. downloads the object with expected SHA-256;
4. decodes Parquet;
5. requires exact candle equality.

A provider-separated manifest and receipt are then uploaded to R2 and SHA-verified.

## Source lineage

Every canonical object records a deterministic digest of the Binance Vision archive filename/SHA pairs used to produce it.

The run-level manifest retains every source archive URL, checksum URL, SHA-256, row count and observed first/last timestamp.

## Not included

This pilot does not yet materialize:

- Mark Price archives;
- Funding Rate history;
- Open Interest history;
- point-in-time Pionex liquidity evidence;
- historical SState evidence.

Those remain separate provider/semantic datasets and must not be mixed into trade-Kline authority.

## Authorization boundary

A PASS proves a provider-separated 2025 Binance trade-Kline dataset and R2 round-trip path for the 15 candidate markets, bounded by actual provider availability.

It does **not** prove:

- Pionex/Binance strategy-signal equivalence;
- eight years of availability for every market;
- the approximately 250-market expansion;
- automatic strategy-plan authority;
- live trading safety or profitability.

The next authorization step after PASS is to freeze the pilot receipt, update the observed storage/cost model, and design the Pionex/Binance equivalence gate before any long-horizon strategy conclusion uses Binance history as a substitute for Pionex-native data.
