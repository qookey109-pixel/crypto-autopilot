# Provider Equivalence V0.2 — Price-Increment Metadata Protocol Draft

Status: **METADATA_PROTOCOL_DRAFT_NOT_AUTHORIZED**

This document defines the metadata evidence that must exist before Provider Equivalence V0.2 can be frozen. It does not authorize metadata acquisition, holdout candle access, provider switching, historical materialization, backtest admission, trade plans, or live trading.

## Why metadata is required

The V0.1 forensic evidence showed that most exact-sign disagreements are one-provider-flat while the other venue moves. V0.2 therefore proposes distinguishing a genuinely directional move from a venue-specific one-price-increment move.

That classification is only defensible if the permitted price increment comes from an independent provider contract. It must never be inferred from the V0.1 mismatches themselves.

## Field semantics — PASS

Semantic authority:

`research/receipts/2026-08-19-provider-equivalence-v0-2-price-increment-semantics.json`

Both provider field meanings are now resolved. This removes the field-semantics blocker only; it does not establish the per-symbol historical values applicable to the candidate holdout.

### Binance USD-M

Official Binance USD-M documentation defines the `PRICE_FILTER` contract and its `tickSize` field as the price-step interval used by the filter.

Future public metadata source:

- USD-M public `/exchangeInfo`
- symbol filter: `filterType=PRICE_FILTER`
- field: `tickSize`

Before use, the future acquisition stage must retain the complete raw response bytes, retrieval time, SHA-256, exact symbol row and exact field path. Missing, duplicate or non-positive values fail closed.

### Pionex Futures

A stronger Pionex authority was found in the official machine-readable repository:

- repository: `pionex-official/pionex-open-api`
- file: `openapi_futures.yaml`
- pre-holdout commit: `b8c63d29ed9b49d967b75b75b0c2ef057e45cc77`
- Git blob: `46f9b20d5ab7946dcb11663913987a511ac5be10`
- field: `FuturesSymbolInfo.quoteStep`
- official description: `Price step size (quote asset)`

That immutable repository snapshot predates the candidate holdout, so the meaning of `quoteStep` is frozen as explicit price-step semantics. The field name alone was not used as proof, and V0.1 price deltas were not used to infer the meaning.

The M1A acquisition artifact was also re-inspected. It contains the selected universe and 45 candle files, but it does **not** retain the raw `/api/v1/common/symbols` response, so it cannot supply historical `quoteStep` values.

## Historical value applicability — ONLY REMAINING METADATA BLOCKER

V0.2 predeclares an unopened candidate holdout:

- `2026-08-03T08:00:00Z`
- through `2026-08-10T07:59:59.999Z`

The schemas prove what the fields mean. They do not by themselves prove the exact per-symbol values effective during that prior period.

A metadata snapshot retrieved now does not automatically prove that the same increment was effective during the holdout.

Before V0.2 freezes, each provider/symbol increment must have an evidence rule showing that the selected value is valid for, or conservative with respect to, the candidate holdout period. The rule itself must be frozen before holdout candles are opened.

No interpolation across metadata versions and no borrowing values between providers is allowed.

## Future acquisition receipt contract

A future authorized metadata-acquisition stage must record at minimum:

- provider and public source URL;
- retrieval timestamp;
- HTTP status and response content type;
- complete raw payload SHA-256;
- exact raw payload retention/reference;
- all 15 expected symbol identities;
- normalized decimal increment per symbol without float rounding;
- exact source field/path per symbol;
- semantic authority per field;
- holdout-applicability authority per value;
- explicit missing/duplicate/non-positive checks;
- `provider_splicing_used=false`;
- `holdout_data_accessed=false`.

No metadata value becomes V0.2 authority merely because it appears plausible.

## Indeterminate-cap design without threshold shopping

The V0.2 direction design needs to prevent excessive `MICROSTRUCTURE_INDETERMINATE` rows from disappearing from the denominator. Rather than add another tunable PASS/REVIEW percentage, draft.2+ derives a hard evidence floor from the unchanged V0.1 minimum-row requirements.

For the exact seven-day holdout:

| Interval | Expected candles | Adjacent comparisons | Minimum comparable | Maximum indeterminate |
|---|---:|---:|---:|---:|
| 15M | 672 | 671 | 599 | 72 |
| 60M | 168 | 167 | 149 | 18 |
| 4H | 42 | 41 | 39 | 2 |

These maxima are mathematical consequences of the existing V0.1 evidence floor, not values selected from V0.1 mismatch performance and not values fitted to the unopened holdout.

If comparable adjacent comparisons fall below the interval minimum, the pair fails closed. There is no post-evidence tuning of an indeterminate percentage.

## Current authorization boundary

Field semantics are frozen, but all of these remain false:

- metadata protocol frozen;
- metadata acquisition authorized;
- historical metadata values authorized;
- metadata values known;
- holdout data access authorized;
- holdout evaluation authorized;
- source switch authorized;
- W1 Trade-Kline materialization authorized;
- Historical Universe membership authorized;
- backtest admission authorized;
- automatic trade plan authorized;
- real-money orders authorized;
- live trading authorized.

## Next required stage

Resolve **historical price-increment value applicability** without opening the holdout.

Only after per-symbol values for both providers are supported by a frozen holdout-applicability rule can a separate V0.2 frozen-protocol authority be proposed. V0.1 remains permanently FAIL regardless of V0.2's future result.
