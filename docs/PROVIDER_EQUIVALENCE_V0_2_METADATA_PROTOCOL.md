# Provider Equivalence V0.2 — Price-Increment Metadata Protocol Draft

Status: **METADATA_PROTOCOL_DRAFT_NOT_AUTHORIZED**

This document defines the metadata evidence that must exist before Provider Equivalence V0.2 can be frozen. It does not authorize metadata acquisition, holdout candle access, provider switching, historical materialization, backtest admission, trade plans, or live trading.

## Why metadata is required

The V0.1 forensic evidence showed that most exact-sign disagreements are one-provider-flat while the other venue moves. V0.2 therefore proposes distinguishing a genuinely directional move from a venue-specific one-price-increment move.

That classification is only defensible if the permitted price increment comes from an independent provider contract. It must never be inferred from the V0.1 mismatches themselves.

## Binance USD-M candidate authority

Official Binance USD-M documentation defines the `PRICE_FILTER` contract and its `tickSize` field as the price-step interval used by the filter.

Candidate future public metadata source:

- USD-M public `/exchangeInfo`
- symbol filter: `filterType=PRICE_FILTER`
- candidate field: `tickSize`

Before use, the future acquisition stage must retain the complete raw response bytes, retrieval time, SHA-256, exact symbol row and exact field path. Missing, duplicate or non-positive values fail closed.

The draft does not yet acquire these values.

## Pionex candidate field and current blocker

Official Pionex Futures common-symbol documentation exposes the public symbols endpoint and includes fields such as:

- `symbol`
- `contractType`
- `quotePrecision`
- `quoteStep`
- `status`

Candidate field: `data.symbols[].quoteStep`.

However, the currently reviewed official page exposes the field without an explicit statement that `quoteStep` is the permitted futures **price increment / tick**. The field name alone is not sufficient authority for V0.2.

Therefore:

- `quoteStep` is only a candidate field;
- `candidate_field_may_be_used_as_v0_2_increment_authority=false`;
- a current market price lattice observation can be supporting evidence only;
- V0.1 candle deltas may not be used to infer the increment;
- the unopened V0.2 holdout may not be sampled to resolve this semantic question.

Acceptable semantic resolution requires an official Pionex source, or separately reviewed public Pionex contract/schema material, that explicitly ties the field to permitted futures price increments.

## Historical applicability blocker

V0.2 predeclares an unopened candidate holdout:

- `2026-08-03T08:00:00Z`
- through `2026-08-10T07:59:59.999Z`

A metadata snapshot retrieved now does not automatically prove that the same increment was effective during that prior period.

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

The V0.2 direction design needs to prevent excessive `MICROSTRUCTURE_INDETERMINATE` rows from disappearing from the denominator. Rather than add another tunable PASS/REVIEW percentage, draft.2 derives a hard evidence floor from the unchanged V0.1 minimum-row requirements.

For the exact seven-day holdout:

| Interval | Expected candles | Adjacent comparisons | Minimum comparable | Maximum indeterminate |
|---|---:|---:|---:|---:|
| 15M | 672 | 671 | 599 | 72 |
| 60M | 168 | 167 | 149 | 18 |
| 4H | 42 | 41 | 39 | 2 |

These maxima are mathematical consequences of the existing V0.1 evidence floor, not values selected from V0.1 mismatch performance and not values fitted to the unopened holdout.

If comparable adjacent comparisons fall below the interval minimum, the pair fails closed. There is no post-evidence tuning of an indeterminate percentage.

## Current authorization boundary

All remain false:

- metadata protocol frozen;
- metadata acquisition authorized;
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

Resolve both of these **without opening the holdout**:

1. Pionex `quoteStep` semantic authority.
2. Historical applicability of each provider's price increment to the candidate holdout.

Only after those are resolved can a separate V0.2 frozen-protocol authority be proposed. V0.1 remains permanently FAIL regardless of V0.2's future result.
