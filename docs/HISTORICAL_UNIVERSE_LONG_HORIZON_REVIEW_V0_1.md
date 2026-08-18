# Historical Universe Long-Horizon Review V0.1

## Purpose

Review the first staged long-horizon Binance acquisition wave against the existing Historical Universe safety model **before** any historical materialization is authorized.

The review resolves an important dependency ordering problem without weakening evidence requirements:

- W1 partition receipts cannot exist before W1 is materialized.
- Historical Universe membership must not be invented from a coverage scan.
- Therefore the pre-materialization review validates only the acquisition scope and the future evidence contract.
- Actual Historical Universe membership remains blocked until audited partition receipts exist.

## Frozen inputs

- Maximum coverage authority: `research/receipts/2026-08-18-binance-max-coverage-discovery.json`
- Staged plan authority: `research/receipts/2026-08-18-binance-staged-expansion-plan.json`
- Historical Universe V0.1: `docs/HISTORICAL_UNIVERSE_V0_1.md`
- Historical Universe -> Backtest Admission V0.1: `docs/HISTORICAL_UNIVERSE_BACKTEST_ADMISSION_V0_1.md`

Target review:

- `W1`
- year `2024`
- required intervals `15M`, `60M`, `4H`
- Binance USD-M research data
- Pionex remains the execution-target exchange

## Two separate concepts

### 1. Acquisition scope review

Coverage authority may be used to determine which Binance-native source archives are eligible to be acquired under a future explicit wave authority.

For W1 the reviewed scope must exactly agree with the frozen staged plan:

- 14 symbols
- 168 symbol-months
- all 14 symbols cover the full 2024 calendar year in the frozen observed window
- HYPEUSDT is excluded because its observed Binance coverage begins in 2025

This review does not download or write any source archive.

### 2. Historical Universe membership authority

Coverage presence is **not** Historical Universe membership authority.

Membership requires actual audited partition receipts containing:

- `provider=binance_usdm`
- `market_type=perp`
- exact interval
- `status=PASS`
- `audit_ok=true`
- actual first/last timestamps
- source SHA-256

Those receipts do not exist for W1 before materialization, so pre-materialization membership count remains zero.

## Provider and provenance rule

Any future W1 Binance partition record is research/proxy evidence relative to the Pionex execution target:

- provider stays `binance_usdm`
- `native=false`
- it must not be inserted as provider `pionex`
- it must not become Pionex-native because symbol mapping or Equivalence later passes

The existing `HistoricalUniverseIndex` provider filter already prevents Binance records from appearing in Pionex snapshots. The review adds tests that freeze this boundary for the W1 evidence path.

## No listing inference

The first observed Binance candle is not an independent listing date.

The review therefore forbids converting coverage onset into `provider_declared_listing` authority. Until independent listing evidence exists, partition evidence can authorize only its actual observed timestamp range.

## Review completion vs authorization

A review PASS means only:

- the W1 acquisition cohort agrees with frozen coverage and staged-plan authority;
- the evidence lifecycle after materialization is defined;
- the circular dependency between review and future partition receipts is resolved without fabricating membership.

It does **not** authorize:

- W1 materialization;
- any Historical Universe backtest membership;
- native Pionex admission;
- source switching;
- provider splicing;
- Pionex-native relabeling;
- automatic trade plans;
- live trading.

## Remaining before W1 materialization

After this review is frozen, W1 still requires:

1. Pionex <-> Binance Equivalence Gate PASS authority.
2. An explicit staged-expansion authority naming W1 and its exact scope.

## Remaining before W1 data may affect backtests

After W1 is materialized, additional evidence is still required:

1. Audited W1 partition receipts for all required intervals.
2. Provider-separated Historical Universe records created only from those receipts.
3. A separate source-switch/proxy-admission authority if Binance data is to substitute for Pionex-native strategy history.

The existing native-only Pionex admission path remains closed until its own authority requirements are satisfied.
