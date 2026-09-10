# Integrated Paper Strategy Challenger V0.3

## Status and boundary

`PREPARED_LOCAL_REPLAY_ONLY`. V0.3 extends the V0.2 paper challenger without
changing formal V0.1, constructing a provider or R2 client, reading the frozen
replacement holdout, scheduling a workflow, promoting a model or authorizing
an order.

## Two evidence lanes

V0.3 runs the same eligible candidate stream through two deliberately separate
research views.

### Portfolio paper evidence

- one position at a time;
- no more than three new trades per UTC day;
- daily -3R new-entry gate;
- current-equity position sizing and an executable equity curve; and
- valid portfolio drawdown, utilization and PnL evidence.

### Independent signal exploration

- overlapping samples are allowed;
- every sample uses the same fixed reference equity;
- no compounding or portfolio concurrency claim is made; and
- aggregate sample PnL may never be labeled portfolio PnL.

This lane is for side, regime, factor, stop and calibration evidence. It speeds
up statistical learning without pretending highly correlated simultaneous
signals could all have been held by the governed one-position portfolio.

The two result objects are returned separately and include
`metricsMayBeCombined=false`.

## Reward-risk diagnostics

The replay records rather than guesses the trade-off created by wider
structural stops:

- eligible and executed stop-distance-in-ATR distributions;
- P50, P75, P90 and P95 stop distances;
- planned fixed-target reward/risk distribution;
- fractions below 1.20R, 1.50R and 2.00R;
- approximate fixed-target breakeven win-rate distribution;
- trade count, win rate, planned R:R and realized R by stop source; and
- leverage-rejected candidate score, side, regime, stop source and stop
  distance.

The approximate breakeven view is descriptive only. It excludes partial exits,
trailing behavior, fees, slippage and funding; realized cost-adjusted R remains
the decision evidence.

## SHORT route

SHORT already has a side-specific technical score, but no formal SState SHORT
score or trading authority. V0.3 labels the bridge as
`CONTEXT_GATE_PLUS_INDEPENDENT_TECHNICAL_SCORE_RESEARCH` and requires the
separate Short Score Calibration V0.1 evidence before promotion review. It
forbids mirroring the formal LONG weights and requires funding stress plus
short-squeeze regime evidence.

## SState gate

The current 0.60/50 gate remains unchanged for compatibility; V0.3 does not
claim it is sufficiently calibrated. SState Gate Calibration V0.1 preregisters
a 3x3 grid over probabilities 0.55/0.60/0.65 and effective sample sizes
50/100/200. A selectable gate must use at least 100 effective samples, nested
walk-forward validation, probability-calibration metrics, regime/side splits,
a Wilson lower-bound gate and Holm family control.

## Promotion

Challenger Promotion Protocol V0.2 retains all V0.1 sample, cost, drawdown,
concentration and side/regime gates and adds:

- at least 180 out-of-sample calendar days;
- at least 28 prospective paper days;
- locked experiment-family registry and SHA-256;
- one frozen primary metric: cost-adjusted net expectancy R;
- at least 5,000 stationary block-bootstrap replicates;
- strictly positive 95% lower confidence bound; and
- Holm-Bonferroni family-wise alpha 0.05 over no more than eight preregistered
  challengers with one evaluation look.

Passing still means only `EVIDENCE_READY_FOR_HUMAN_REVIEW`.

## Files

- `config/integrated_paper_strategy_v0_3.json`
- `src/crypto_autopilot/integrated_paper_strategy_v0_3.py`
- `tests/test_integrated_paper_strategy_v0_3.py`
- `config/challenger_promotion_protocol_v0_2.json`
- `config/challenger_experiment_registry_v0_1.json`
- `src/crypto_autopilot/challenger_promotion_v0_2.py`
- `config/sstate_gate_calibration_v0_1.json`
- `config/short_score_calibration_v0_1.json`
