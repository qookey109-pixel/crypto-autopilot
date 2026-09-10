# Challenger Promotion Protocol V0.1

## Meaning

This protocol is a fail-closed evidence gate, not promotion authority. It was
prepared before the integrated challenger consumes real out-of-sample results.
A passing package becomes eligible for human review only.

## Common gates

- lineage complete, no look-ahead and exact provider separation;
- replacement holdout untouched and formal V0.1 unchanged;
- at least four chronological walk-forward folds;
- at least 75% of ready folds have positive net expectancy;
- at least 300 out-of-sample trades for the core LONG/SHORT track;
- median net expectancy at least +0.05R;
- doubled-cost/stress net expectancy at least 0R;
- maximum drawdown no greater than 25%;
- no symbol contributes more than 10% of trades;
- leverage-cap rejection fraction no greater than 35%; and
- challenger expectancy is not below the governed baseline.

The total fold trade count must exactly match the reported out-of-sample total.
Malformed evidence raises instead of being treated as a strategy loss.

## Core LONG/SHORT track

- at least 100 LONG and 100 SHORT out-of-sample trades;
- at least 50 trades in each of `TREND_UP`, `TREND_DOWN` and `RANGE`.

## Tokenized-equity track

- at least 150 out-of-sample trades across at least three symbols;
- 100% session-policy coverage;
- 100% corporate-action-policy coverage; and
- explicit spread-stress PASS.

## Result semantics

- `REJECT`: evidence is incomplete, malformed or below one or more gates.
- `EVIDENCE_READY_FOR_HUMAN_REVIEW`: quantitative gates passed, but no strategy
  change is authorized.

Both results preserve `automatic_model_promotion_authorized=false`,
`automatic_trade_plan_authorized=false`, `real_money_order_authorized=false`
and `live_trading_authorized=false`.

