# Historical Data V0.1

## Purpose

M1 establishes a deterministic, public-data-only pipeline for selecting a controlled Pionex perpetual-futures universe and backfilling the 15M / 60M / 4H candles needed by SState Intraday Wave research.

No API key or live-trading permission is used.

## Universe selection

Inputs:

1. Active `PERP` symbols with `status=TRADING`.
2. Futures 24-hour tickers.
3. Futures best bid/ask (`bookTicker`).

V0.1 keeps USDT perpetual contracts only, rejects missing/invalid quotes and spreads above the configured limit, then ranks by:

1. exchange-reported 24h `amount` descending;
2. spread ascending;
3. symbol ascending for deterministic ties.

`amount` is only compared inside the same USDT-quoted universe. It is an exchange-reported turnover field, not a cross-currency normalization layer.

Target universe size is 15; acceptable operating range is 10–20.

## Historical pagination

Pionex futures klines use an inclusive `endTime` and return at most 500 candles per request.

Backfill therefore proceeds backward:

```text
requested endTime
      |
      v
page of <= 500 candles
      |
      v
earliest candle time - 1 ms
      |
      v
next endTime
```

Using `earliest_time - 1` prevents boundary duplication between pages.

The collector requires explicit start and end boundaries so repeated runs over the same exchange history use the same requested range.

## Integrity audit

Every backfill is audited for:

- duplicate timestamps;
- out-of-order timestamps;
- missing interval gaps;
- timestamps not aligned to the requested interval;
- invalid/non-finite OHLCV;
- high/low consistency;
- negative volume.

An audit failure is evidence to investigate; the collector does not silently fill or interpolate missing candles.

## Storage policy

During M1, small deterministic JSON fixtures may be used for testing. Bulk market history must not be committed to GitHub.

Target Cloudflare R2 layout:

```text
market/pionex/futures/<SYMBOL>/15m/YYYY-MM.parquet
market/pionex/futures/<SYMBOL>/1h/YYYY.parquet
market/pionex/futures/<SYMBOL>/4h/YYYY.parquet
```

R2/Parquet persistence is intentionally deferred until the public backfill/audit path is proven.

## Commands

Select the current universe:

```bash
python scripts/select_pionex_universe.py --target-size 15
```

Backfill one explicit range:

```bash
python scripts/backfill_pionex_history.py BTC_USDT_PERP 15M \
  --start 2026-01-01T00:00:00Z \
  --end 2026-08-01T00:00:00Z \
  --output /tmp/BTC_USDT_PERP-15M.json
```

The command exits non-zero when its integrity audit fails.
