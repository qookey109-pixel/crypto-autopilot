# Provider Equivalence V0.2 — Forward Metadata Capture

Status: **METADATA CAPTURE AUTHORIZED / HOLDOUT CANDLES FORBIDDEN**

Authority:
`research/receipts/2026-08-19-provider-equivalence-v0-2-forward-metadata-capture-authority.json`

Protocol:
`config/provider_equivalence_v0_2_metadata_capture_v0_1.json`

## Why the prior unopened candidate was superseded

The original candidate window `2026-08-03T08:00:00Z` through `2026-08-10T07:59:59.999Z` was never accessed or evaluated. Provider field semantics were later proven, but authoritative per-symbol increment values were not preserved for that historical period. Current metadata must not be backfilled into the past.

Therefore the old candidate is superseded **before any holdout evidence**.

## New frozen candidate holdout

- `2026-08-21T00:00:00Z`
- through `2026-08-27T23:59:59.999Z`
- same 15 frozen symbols
- same `15M / 60M / 4H`
- 45 mapped pairs
- candle access: **false**
- evaluation: **false**

The future holdout exists only so metadata applicability can be measured contemporaneously.

## Metadata capture window

Capture public metadata from:

- `2026-08-20T00:00:00Z`
- through `2026-08-28T01:59:59.999Z`

There are 194 UTC hourly coverage slots: 24 hours before the holdout, all 168 holdout hours, and two hours after the holdout.

Two scheduled attempts are planned per hour, at UTC minute 17 and 47. Final applicability requires at least one complete valid capture in every hourly slot. Multiple captures are allowed only if the normalized 15-symbol provider vectors agree.

Any missing hourly slot or any observed increment/status-vector change makes the metadata applicability result INVALID and the holdout candles remain unopened.

## Provider metadata

Pionex:

- public `GET /api/v1/common/symbols`
- official OpenAPI describes it as all futures trading-pair information
- price step field: `quoteStep`

Binance USD-M:

- public `GET /fapi/v1/exchangeInfo`
- official exchange-information contract has no symbol request parameter
- request weight 1
- price step field: `PRICE_FILTER.tickSize`

Both raw provider payloads are retained for each complete capture.

## Storage

Only the dedicated metadata namespace is authorized:

`metadata/provider-equivalence/v0_2/forward-holdout-20260821/`

Each complete capture writes three immutable run-scoped objects:

1. `pionex-symbols.json.gz`
2. `binance-usdm-exchange-info.json.gz`
3. `receipt.json` written last

Raw and compressed SHA-256 values are recorded. Every object is read back and verified. Overwrite and delete are forbidden.

The frozen conservative storage cap for this phase is 4 GiB. Combined with the current bucket reference of 22,120,404 bytes, this remains below the existing 10 GB project storage block guardrail.

## Authorization boundary

This phase authorizes public metadata capture and metadata-only R2 writes only.

It does **not** authorize:

- old holdout reactivation;
- any holdout candle request;
- holdout evaluation;
- provider source switching;
- provider splicing;
- Pionex-native relabeling;
- Trade-Kline W1 materialization;
- Historical Universe membership;
- backtest admission;
- strategy changes;
- automatic trade plans;
- real-money orders;
- live trading.

Even a future metadata-applicability PASS will not automatically open the holdout. A separate versioned holdout-access authority is required.
