# Core100 Training REJECT Diagnosis — 2026-09-15

Status: INITIAL DIAGNOSIS RECORD

This document records the first post-training diagnosis for the completed Binance USD-M Crypto Core 100 Training V0.1.2 run.

## Observed training outcome

Workflow run: `34918219864`

- workflow status: completed
- workflow conclusion: success
- training report status: PASS
- symbol_count: 100
- dataset_partition_objects: 14274
- dataset_rows: 18235427
- example_count: 249228
- dataset_fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`

## Model quality gate

- `all_folds_ready = true`
- `all_folds_beat_naive_log_loss = false`
- `all_base_cost_scenarios_positive_average_return = false`
- `automatic_promotion = false`
- `status = REJECT`

## Interpretation

The training pipeline itself completed correctly and published its governed training artifacts. The rejection is a model-quality outcome, not a workflow failure.

The two blocking conditions are:

1. At least one evaluation fold does not beat the naive log-loss baseline.
2. At least one base transaction-cost scenario does not produce positive average return.

These conditions must be diagnosed before any retraining or model-promotion work. Historical data acquisition is already complete and must not be restarted solely because of this REJECT outcome.

## Safety boundary

This diagnosis does not authorize:

- automatic model promotion
- formal trade plans
- real-money orders
- live trading
- source switching
- Pionex-native relabeling

## Next diagnostic work

1. Extract fold-level metrics from the published training metrics object.
2. Rank folds by log-loss delta versus naive baseline.
3. Rank base-cost scenarios by average return.
4. Identify whether the failure is concentrated by fold, symbol cohort, regime, or cost sensitivity.
5. Only then decide whether the next change belongs in features, labels, model configuration, or strategy gating.
