# Pionex ↔ Binance Equivalence Gate V0.1 — Frozen Result

Date: 2026-08-19

## Result

The frozen V0.1 provider-equivalence protocol produced a definitive **FAIL** after all required Binance Vision daily archives became available.

Authority: `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json`

Evidence run: `32206479914`

- execution status: `PASS`
- gate status: `FAIL`
- evaluated pairs: `45 / 45`
- PASS: `18`
- REVIEW: `18`
- FAIL: `9`
- Binance Vision daily archives: `360`
- source switch authorized: `false`
- full strategy signal equivalence: `DEFERRED_UNDEFINED_STRATEGY_RULES`

## Failure shape

All nine FAIL pairs failed the already-frozen `return_direction_agreement` criterion.

By interval:

- `15M`: 4 PASS / 4 REVIEW / 7 FAIL
- `60M`: 5 PASS / 8 REVIEW / 2 FAIL
- `4H`: 9 PASS / 6 REVIEW / 0 FAIL

Failed pairs:

- ADA `15M`, `60M`
- UNI `15M`, `60M`
- XRP `15M`
- LTC `15M`
- DOGE `15M`
- INJ `15M`
- SUI `15M`

The evidence also contains 18 REVIEW results, dominated by `return_direction_agreement_review`; two `60M` pairs additionally hit `setup_60m_agreement_review`.

## Interpretation boundary

This result is not an execution failure and is no longer a source-publication delay. The full frozen 45-pair evidence set exists and the V0.1 aggregate Gate is FAIL.

Therefore:

- do not lower V0.1 thresholds after evidence;
- do not shrink the frozen 15-symbol / 45-pair scope to manufacture PASS;
- do not relabel Binance history as Pionex-native;
- do not splice providers;
- do not authorize Binance → Pionex source switching;
- do not authorize staged Trade-Kline W1 materialization;
- do not claim full strategy-signal equivalence while the six strategy semantics remain undefined;
- live trading remains forbidden.

## Next work

The only authorized next step is **forensic review** of the V0.1 FAIL result without changing the frozen V0.1 decision.

A future V0.2 equivalence protocol may be proposed only if the forensic review demonstrates a concrete measurement defect or a separately justified research question. Any V0.2 protocol must be versioned and frozen before its own evidence is evaluated. It cannot retroactively rewrite V0.1.

The hourly source-publication retry is removed because source publication is no longer pending. Manual execution remains available for reproducibility and forensic checks.
