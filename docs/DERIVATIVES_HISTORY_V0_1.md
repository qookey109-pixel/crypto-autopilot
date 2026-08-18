# Derivatives Historical Data V0.1

Status: **FRAMEWORK_ONLY / PAPER-ONLY**

This document defines the evidence and no-lookahead boundary for Pionex perpetual funding rate, mark price and open interest data. It does not claim that a real long-horizon derivative-data dataset has already been acquired or frozen PASS.

## Provider capability boundary

The Pionex public futures API currently documents three materially different capabilities:

| Data | Public endpoint | Historical capability used by V0.1 | Project treatment |
| --- | --- | --- | --- |
| Funding rate | `/api/v1/market/fundingRates` | Historical query with `endTime`; limit up to 500 | Backward historical pagination is authorized after audit |
| Mark price | `/api/v1/market/markKlines` | Bounded/latest Kline request; current documentation does not define `endTime` | Do not invent deep-history pagination; capture only documented window |
| Open interest | `/api/v1/market/openInterests` | Current snapshot | Capture point-in-time snapshots only; no historical backprojection |

The support matrix is frozen in `config/derivatives_history_v0_1.json`.

## Funding rate historical authority

`FundingRateRecord` freezes:

- symbol;
- exact provider `fundingTime`;
- funding rate;
- retrieval response timestamp.

Historical acquisition uses backward pagination from an explicit end time. The next cursor is `earliest_funding_time - 1 ms`. No fixed 1h/8h cadence is assumed because the provider may vary funding intervals.

Exact duplicate observations across inclusive/adjacent pages may be deduplicated. Conflicting rates at the same symbol + funding timestamp fail closed.

After audit, records may be converted one-for-one into Backtest Engine `FundingPoint` values. The timestamp is never shifted. A positive rate remains a cost to a V0.1 LONG position under the existing Backtest Engine funding formula.

## Mark price evidence

`MarkPriceCandle` is OHLC-only. It intentionally does not fabricate volume.

A mark-price candle is not usable before the end of its interval:

`available_at_ms = time_ms + interval_ms`

V0.1 audits strict timestamp uniqueness, OHLC validity, single-interval consistency and contiguous bars when continuity is required.

The current project client intentionally has no `end_time_ms` argument for `get_mark_price_klines`. This is deliberate: the current provider documentation does not define that parameter for mark-price Klines. Adding an undocumented cursor would create false historical authority.

Calendar-month `1m` mark-price candles are excluded from V0.1 because the fixed-millisecond closed-bar calculation used by this foundation is not appropriate for variable-length calendar months.

## Open interest evidence

The current public endpoint is treated as a snapshot source.

`OpenInterestSnapshot` freezes:

- symbol;
- open-interest value;
- provider response timestamp as `observed_at_ms`.

An OI observation may only be used at or after `observed_at_ms`, subject to an explicit maximum-age gate. A later snapshot can never authorize or reconstruct an earlier historical timestamp.

This means historical OI for dates before the project began capturing snapshots remains **UNAVAILABLE**, not zero and not inferred.

## No-lookahead rules

1. Funding settlements retain the provider's exact historical funding timestamp.
2. Mark-price OHLC is consumable only after the mark bar closes.
3. OI snapshots are consumable only at/after the actual response timestamp.
4. Later snapshots are never substituted for missing earlier evidence.
5. Missing provider history is an evidence gap, not a strategy failure.
6. No silent interpolation or synthetic reconstruction is allowed in V0.1.

## Public-client additions

`PionexPublicClient` now exposes public-only methods:

- `get_funding_rates(...)`
- `get_mark_price_klines(...)`
- `list_open_interests()`

No API key, signature, account, position or order path is introduced.

## What is still not complete

- No real one-year funding-rate backfill receipt is frozen PASS yet.
- No mark-price historical-depth proof beyond the documented bounded/latest window is frozen.
- No historical OI dataset exists for time before snapshot capture begins.
- Mark price and OI are not yet wired into strategy scoring.
- Funding-rate evidence is not yet materialized to R2 as a frozen authority dataset.
- Long-horizon storage/cost estimates for these derivative datasets are not yet part of the R2 budget gate.
- No live-trading authorization exists.
