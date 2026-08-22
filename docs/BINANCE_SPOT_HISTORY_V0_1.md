# Binance Spot History V0.1

## Purpose

Historical specification for the former local 15-symbol Binance Spot dataset.
This flow is retired and superseded by the R2-only full-market V0.3 pipeline.
No raw history or spot chart is published to GitHub Pages.

## Data products

The former ignored local data products were removed. The legacy script now
requires explicit output paths and accepts only GitHub Actions workspace paths or
system temporary directories; it cannot persist generated data in the repository.

## Provider and authority boundary

- provider is always `binance_spot`;
- no Pionex-native relabeling or provider splicing;
- V0.1 itself has no production R2 reads or writes and is no longer an active flow;
- no Trade-Kline W1 materialization;
- no holdout access;
- no source switch, formal trade plan, real-money order or live trading;
- GitHub Pages projection is retired and unauthorized.

`HYPEUSDT` is retained in the requested universe but currently reports
`NO_DATA` because Binance Spot rejects it as an invalid market. No alternate
provider is silently substituted.

## Historical result

The 2026-08-22 run fetched 31,402 audited daily candles across 14 Binance
Spot markets through 2026-08-21. Every available series passed duplicate,
ordering, alignment, gap and OHLCV validity checks.
