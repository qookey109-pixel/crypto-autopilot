# Pionex ↔ Binance Provider Equivalence V0.2 — Design Draft

Status: **PROTOCOL_DRAFT_NOT_AUTHORIZED**

This is a design document only. It does not authorize acquisition or evaluation of V0.2 holdout candles, provider switching, historical materialization, backtest admission, trade plans, or live trading.

## Why V0.2 exists

V0.1 is permanently frozen as FAIL:

- 45 / 45 pairs evaluated.
- 18 PASS / 18 REVIEW / 9 FAIL.
- all nine FAIL pairs include `return_direction_agreement_fail`.

The V0.1 forensic replay then showed that exact-sign direction disagreement is dominated by a specific microstructure shape:

- 539 / 623 all-pair mismatches are one-provider-flat.
- 388 / 432 mismatches inside the nine FAIL pairs are one-provider-flat.
- 44 failed-pair mismatches are still true opposite non-zero signs.
- 16 failed-pair mismatches exceed 10 bps.

Therefore V0.2 must not simply add a post-hoc tiny-return deadband. V0.1 remains FAIL regardless of what happens later.

## Independent holdout is declared now and must remain unopened

Candidate V0.2 holdout:

- start: `2026-08-03T08:00:00Z`
- end: `2026-08-10T07:59:59.999Z`
- same frozen 15-symbol M1A universe
- `15M`, `60M`, `4H`
- 45 mapped provider pairs

This window immediately precedes V0.1 and does not overlap it.

**Important:** the candidate holdout must not be fetched, previewed, manually sampled, or evaluated while this document is still a draft. A later frozen V0.2 authority must explicitly authorize access.

## Metrics intentionally retained from V0.1

To avoid unnecessary threshold shopping, V0.2 proposes carrying the following V0.1 metrics unchanged:

### Price proximity

- median OHLC bps: PASS <= 10, REVIEW <= 25
- p95 open/close bps: PASS <= 25, REVIEW <= 75
- p95 high/low bps: PASS <= 75, REVIEW <= 200

### 60M setup-state agreement

- PASS >= 0.98
- REVIEW >= 0.95
- minimum ready bars = 100
- state remains `ema20_gt_ema50`, `ema20_slope_positive`, `close_gt_ema20`

### Minimum comparable rows

Proposed minimums remain:

- 15M: 600
- 60M: 150
- 4H: 40

## Proposed direction measurement

The raw close-to-close state remains exact:

- positive delta = `UP`
- zero delta = `FLAT`
- negative delta = `DOWN`

V0.2 does **not** redefine a non-zero return as zero by an arbitrary bps deadband.

Instead, it proposes a separately observable microstructure classification based on each venue's **verified price increment** for that exact symbol and holdout period.

For an adjacent pair of candles:

1. Same raw direction on both providers → `COMPARABLE_MATCH`.
2. Opposite non-zero directions → `COMPARABLE_MISMATCH`.
3. Exactly one provider is flat and the other moves **more than one verified price increment** of the moving provider → `COMPARABLE_MISMATCH`.
4. Exactly one provider is flat and the other moves **at most one verified price increment** of the moving provider → `MICROSTRUCTURE_INDETERMINATE`.

Only `COMPARABLE_MATCH + COMPARABLE_MISMATCH` enters the proposed direction-agreement denominator.

The proposed agreement PASS/REVIEW values remain 0.98 / 0.95, copied from V0.1 rather than tuned on the unseen V0.2 holdout.

## Why an indeterminate-fraction gate is required

Excluding microstructure-indeterminate rows from the direction denominator could otherwise hide too much venue disagreement. Therefore V0.2 must also grade:

`MICROSTRUCTURE_INDETERMINATE / all adjacent comparisons`

The PASS/REVIEW caps for this metric are **deliberately unresolved in this draft**. They must be selected and justified before any holdout access. The holdout cannot be used to choose them.

Until these caps are frozen, V0.2 cannot be executed as a Gate.

## Required price-increment authority before freeze

Observed V0.1 price deltas are not accepted as tick-size evidence.

Before V0.2 can freeze, a separate public-metadata evidence step must establish for all 15 mapped symbols:

- Pionex price increment / price-step authority.
- Binance USD-M price increment / price-step authority.
- public source provenance.
- raw payload SHA-256 receipts.
- exact JSON field/path or equivalent source field.
- evidence that the value is applicable during the candidate holdout.

No metadata value may be interpolated or borrowed from the other provider.

## Fail-closed requirements

A frozen V0.2 protocol must fail closed on:

- missing symbol metadata;
- metadata that cannot be tied to the holdout period;
- missing provider pair;
- timestamp-set mismatch;
- candle audit failure;
- source checksum/revision mismatch;
- insufficient comparable rows;
- unresolved thresholds.

Volume remains excluded from provider-equivalence grading because venue volume is venue-specific.

## What this draft does not authorize

The following remain false:

- `protocol_frozen`
- `metadata_acquisition_authorized`
- `holdout_data_access_authorized`
- `holdout_evaluation_authorized`
- `source_switch_authorized`
- `provider_splicing_authorized`
- `staged_trade_kline_w1_materialization_authorized`
- `historical_universe_membership_authorized`
- `backtest_admission_authorized`
- `automatic_trade_plan_authorized`
- `real_money_order_authorized`
- `live_trading_authorized`

## Next design step

Before any V0.2 holdout evidence is touched:

1. define and validate the public price-increment metadata acquisition protocol;
2. choose and justify the indeterminate-fraction PASS/REVIEW caps independently of the holdout;
3. freeze the complete V0.2 config and its exact source/metadata contracts in a new authority receipt;
4. only then permit one holdout execution.

PASS, REVIEW and FAIL must all remain acceptable outcomes. No threshold or scope may change after that holdout is evaluated without creating another new protocol version.
