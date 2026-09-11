# Pionex Historical Reach Discovery V0.3

Status: **AUTHORIZED AFTER PROTECTED-MAIN MERGE — MANUAL DISCOVERY ONLY**

## Purpose

The 27-day V0.2 pilot proved one bounded Pionex-native K-line sample can be
collected, validated, written to R2 and frozen without opening the replacement
holdout. It did **not** prove the maximum native history available from Pionex.

V0.3 answers one narrower question before any large materialization:

> For `BTC_USDT_PERP`, how far back can the public Pionex K-line endpoint be
> traversed for `15M`, `60M`, `4H`, `1D`, and `1W` before either the provider's
> returned history ends or the documented 10,000-record ceiling is reached?

The output is metadata only. No candles or raw provider payloads are persisted.

## Official provider contract

Pinned provider specification:

- repository: `pionex-official/pionex-open-api`
- commit: `d31e146006da7b59c228c07e11949ec8fb7140de`
- endpoint: `GET /api/v1/market/klines`
- page limit: 500
- documented maximum: 10,000 records
- authentication: public market-data request; no API key required
- futures interval enum includes `15M`, `60M`, `4H`, `1D`, and `1W`
- Pionex documents weekly bars as starting Monday UTC 00:00
- the provider interval enum does **not** contain a native `1Y` interval

Private account/trading API credentials are intentionally not part of this
discovery path.

## Fixed scope

- symbol: `BTC_USDT_PERP`
- provider-native intervals: `15M`, `60M`, `4H`, `1D`, `1W`
- `1Y` is explicitly non-native and may only be derived from validated `1D`
  evidence under a later separately versioned authority
- latest admissible candle: strictly before `2026-08-28T00:00:00Z`
- the discovery cursor is the last completed provider-aligned candle before the
  cutoff; for `1W`, Monday UTC 00:00 alignment is preserved
- page size: 500
- maximum records per interval: 10,000
- maximum data pages per interval: 20
- one optional one-record boundary probe after a short page
- total request ceiling: 105
- no automatic schedule
- manual `workflow_dispatch` only
- no R2 read/write
- no holdout access
- no materialization
- no yearly aggregation in this stage
- no backtest/training/trade/live authority

## Boundary classification

Each provider-native interval must end in exactly one success classification.

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
- use Monday UTC 00:00 alignment for weekly candles;
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

Expected outcomes may differ by interval. At the 10,000-record ceiling, the
nominal capacity is roughly 104 days at 15 minutes, 417 days at 60 minutes,
1,667 days at 4 hours, 27.4 years at 1 day, and 191.6 years at 1 week. These are
capacity conversions only; actual Pionex history will normally be bounded by the
market's real provider history well before the larger theoretical spans.

There is no provider-native `1Y` candle in this authority. If yearly bars are
useful later, they must be deterministically aggregated from already validated
`1D` Pionex-native bars with explicit calendar-year boundaries and separate
lineage, rather than being mislabeled as provider-native yearly K-lines.

After a reviewed PASS report:

1. freeze the exact reach evidence;
2. choose the native materialization range independently for each interval;
3. materialize only under a new versioned authority;
4. optionally define a separate deterministic `1Y` derivation contract from
   validated `1D` history;
5. keep any longer Binance USD-M research history provider-separated;
6. never relabel Binance data as Pionex-native;
7. admit Pionex K-lines + Pionex funding into Simulation Readiness only through
   a later reviewed data-admission step.

## Explicit non-authority

A V0.3 discovery PASS does not authorize or prove:

- full multi-year Pionex materialization;
- native Pionex `1Y` candles;
- yearly aggregation;
- Top-100 or 150-market materialization;
- R2 writes;
- replacement-holdout access;
- model training or model quality;
- strategy profitability;
- source switching;
- live trade plans;
- real-money orders.

Config SHA-256: `ba7ffaaed06be43fd48348529282d078a7ffcb267957832075097cb5fa6648af`
