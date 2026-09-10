# Pionex Historical Reach Discovery V0.3

Status: **AUTHORIZED AFTER PROTECTED-MAIN MERGE — MANUAL DISCOVERY ONLY**

## Purpose

The 27-day V0.2 pilot proved one bounded Pionex-native K-line sample can be
collected, validated, written to R2 and frozen without opening the replacement
holdout. It did **not** prove the maximum native history available from Pionex.

V0.3 answers one narrower question before any large materialization:

> For `BTC_USDT_PERP`, how far back can the public Pionex K-line endpoint be
> traversed for `15M`, `60M`, and `4H` before either the provider's returned
> history ends or the documented 10,000-record ceiling is reached?

The output is metadata only. No candles or raw provider payloads are persisted.

## Official provider contract

Pinned provider specification:

- repository: `pionex-official/pionex-open-api`
- commit: `d31e146006da7b59c228c07e11949ec8fb7140de`
- file: `openapi.yaml`
- blob: `6aee44bce634b695ead4caeb051bd8d036db896a`
- endpoint: `GET /api/v1/market/klines`
- page limit: 500
- documented maximum: 10,000 records
- authentication: public market-data request; no API key required

Private account/trading API credentials are intentionally not part of this
discovery path.

## Fixed scope

- symbol: `BTC_USDT_PERP`
- intervals: `15M`, `60M`, `4H`
- latest admissible candle: strictly before `2026-08-28T00:00:00Z`
- page size: 500
- maximum records per interval: 10,000
- maximum data pages per interval: 20
- one optional one-record boundary probe after a short page
- total request ceiling: 63
- no automatic schedule
- manual `workflow_dispatch` only
- no R2 read/write
- no holdout access
- no materialization
- no backtest/training/trade/live authority

## Boundary classification

Each interval must end in exactly one success classification.

### `PROVIDER_EARLIEST_REACHED`

A page contains fewer than the requested number of rows and a one-record probe
immediately before its oldest candle returns no earlier candle, or a later
pagination request returns no rows after already observing a continuous valid
history.

This is evidence of the earliest history reachable through the provider API
under this contract. It is not a claim about data that may exist outside the API.

### `DOCUMENTED_RECORD_CAP_REACHED`

Exactly 10,000 continuous valid records are observed before a provider earliest
boundary is proven. Discovery stops without requesting record 10,001.

This means the provider API ceiling, not the market listing date, limits the
observed reach. The true earlier Pionex-native history remains unknown.

## Integrity rules

Every returned page must:

- contain no more rows than requested;
- end exactly at the requested aligned cursor;
- be internally continuous and aligned for the interval;
- contain valid finite positive OHLC values and non-negative volume;
- contain no duplicate timestamps inside or across pages;
- remain strictly before the replacement-holdout boundary.

A provider error, inconsistent short page, timestamp gap, invalid candle,
duplicate, cursor regression, request-budget exhaustion or empty first page
fails closed.

No missing candle is filled, interpolated, copied or inferred.

## How this supports the 9/15 simulation target

The reach report decides the historical-data architecture rather than assuming
that every interval can provide the same number of years.

Expected outcomes may differ by interval. For example, a 10,000-record ceiling
corresponds to roughly 104 days at 15 minutes, 417 days at 60 minutes, and
1,667 days at 4 hours. These are capacity conversions, not claims about what
Pionex will actually return.

After a reviewed PASS report:

1. freeze the exact reach evidence;
2. choose the native materialization range independently for each interval;
3. materialize only under a new versioned authority;
4. keep any longer Binance USD-M research history provider-separated;
5. never relabel Binance data as Pionex-native;
6. admit Pionex K-lines + Pionex funding into Simulation Readiness only through
   a later reviewed data-admission step.

## Explicit non-authority

A V0.3 discovery PASS does not authorize or prove:

- full multi-year Pionex materialization;
- Top-100 or 150-market materialization;
- R2 writes;
- replacement-holdout access;
- model training or model quality;
- strategy profitability;
- source switching;
- live trade plans;
- real-money orders.

Config SHA-256: `02a95c0b20fa9f39d47a184ace1cb05d29c5aa593d9d6b64bffced5a69563b97`
