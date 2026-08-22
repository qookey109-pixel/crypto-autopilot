# Binance Spot History V0.1

## Purpose

Provide a local, provider-separated Binance Spot daily history dataset and a
read-only GitHub Pages chart projection for the frozen 15-symbol candidate
list. The requested range begins at `2020-01-01T00:00:00Z` and ends at the
latest complete UTC day.

## Data products

The manual fetch command writes ignored local research artifacts:

- `artifacts/binance-spot-history-v0-1/binance-spot-daily-2020-to-present.csv.gz`
- `artifacts/binance-spot-history-v0-1/binance-spot-daily-2020-to-present.parquet`
- `artifacts/binance-spot-history-v0-1/receipt.json`

It also writes the reviewed, down-sampled dashboard projection:

- `web/data/binance-spot-history.json`

Run it with:

```bash
PYTHONPATH=src .venv/bin/python scripts/fetch_binance_spot_history.py
```

## Provider and authority boundary

- provider is always `binance_spot`;
- no Pionex-native relabeling or provider splicing;
- no production R2 reads or writes;
- no Trade-Kline W1 materialization;
- no holdout access;
- no source switch, formal trade plan, real-money order or live trading;
- the dashboard projection is a normalized read-only view, not authority.

`HYPEUSDT` is retained in the requested universe but currently reports
`NO_DATA` because Binance Spot rejects it as an invalid market. No alternate
provider is silently substituted.

## Current local result

The 2026-08-22 local run fetched 31,402 audited daily candles across 14 Binance
Spot markets through 2026-08-21. Every available series passed duplicate,
ordering, alignment, gap and OHLCV validity checks.
