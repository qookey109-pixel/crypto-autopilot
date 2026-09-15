# Challenger Promotion Protocol V0.2

## Purpose

V0.2 preserves the V0.1 quantitative gates and adds safeguards against a
challenger passing because many variants were tested. The protocol was
prepared before Integrated V0.3 result evidence is read.

## Existing quantitative gates retained

- four chronological walk-forward folds and at least 75% positive folds;
- 300 out-of-sample trades for CORE LONG/SHORT;
- 100 LONG and 100 SHORT trades;
- 50 trades in each trend-up, trend-down and range regime;
- median net expectancy at least +0.05R;
- non-negative cost-stress expectancy;
- maximum drawdown 25%;
- maximum single-symbol fraction 10%;
- maximum leverage-rejection fraction 35%; and
- challenger expectancy not below the governed baseline.

## Duration and calibration gates

- at least 180 out-of-sample calendar days;
- at least 28 prospective paper days;
- SState calibration ready, family-adjusted and holdout untouched;
- selected SState gate has at least 100 effective samples, four outer folds and
  Wilson lower bound at least 0.50; and
- CORE SHORT has at least 100 independently calibrated samples, funding-stress
  PASS and short-squeeze regime evidence.

## Time-series confidence

The primary metric is frozen as `net_expectancy_r_after_costs`. Evidence must
use at least 5,000 stationary block-bootstrap replicates, preserve serial
dependence and produce a strictly positive 95% lower confidence bound.

## Multiple comparisons

Every evaluated challenger belongs to one locked family with a registry
SHA-256. The family may contain no more than eight challengers and all family
p-values must be supplied. V0.2 applies Holm-Bonferroni at family-wise alpha
0.05 with exactly one evaluation look. A missing candidate, changed family,
incomplete p-value set or non-significant adjusted result fails closed.

The locked registry currently defines:

- `CORE_INTRADAY_DIRECTIONAL_V0_1`: formal SState baseline, Paper Training,
  Paper Exploration, LONG/SHORT V0.2 and Integrated V0.3; and
- `TOKENIZED_EQUITY_V0_1`: Tokenized Equity V0.1 and its Integrated V0.3
  adapter.

Binance Spot Shadow remains in a separate non-comparable family because its
data, horizon, feature and execution assumptions differ. It requires a separate
versioned promotion protocol rather than being pooled into the same p-value
family.

## Meaning of PASS

`EVIDENCE_READY_FOR_HUMAN_REVIEW` is not automatic promotion, a formal strategy
change, a trade plan, an order or live-trading authority.
