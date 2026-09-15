# Core100 Training REJECT Diagnosis — 2026-09-15

Status: THRESHOLD SWEEP 0.50–0.55 COMPLETE

This document records the completed post-training diagnosis for Binance USD-M Crypto Core 100 Training V0.1.2 through the bounded threshold-sweep stage. It does not authorize retraining, model promotion, threshold changes, trade plans, holdout access or live trading.

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

The pipeline completed correctly. `REJECT` is a model-quality outcome, not a workflow failure.

## Fold-level log-loss diagnosis

Only `fold-1` fails the naive log-loss baseline:

| Fold | Model log loss | Naive log loss | Delta vs naive | Result |
| --- | ---: | ---: | ---: | --- |
| fold-1 | 0.6868440595 | 0.6866175783 | +0.0002264813 | FAIL |
| fold-2 | 0.6876643790 | 0.6879491830 | -0.0002848040 | PASS |
| fold-3 | 0.6838030058 | 0.6849980627 | -0.0011950569 | PASS |
| fold-4 | 0.6870128737 | 0.6877861655 | -0.0007732918 | PASS |

This remains an independent blocker even if a threshold later produces positive trading diagnostics.

## Configured threshold 0.55 diagnosis

The configured `probability_threshold = 0.55` emitted zero signals in all four folds. The base-cost gate therefore failed with zero average return because there were no selected trades. It did not demonstrate that selected trades lost after fees.

## Exact one-shot threshold replay

Replay run: `34936331199`

Artifact:

- id: `10387278663`
- name: `core100-threshold-sweep-replay-34936331199-1`
- digest: `sha256:f983f5364024a911be3f930fce641bd750922a8d95e710951b88d5738f5cfa29`
- replay head: `fbebb5cbe424e4a6d6c33cb6e09a12da4849ee07`

The replay used the exact governed dataset fingerprint and completed successfully without publishing a new model or writing to R2.

### Probability upper tail

| Fold | Samples | p99 | Maximum |
| --- | ---: | ---: | ---: |
| fold-1 | 32,147 | 0.481398 | 0.517649 |
| fold-2 | 28,610 | 0.469716 | 0.511855 |
| fold-3 | 29,155 | 0.470860 | 0.499426 |
| fold-4 | 27,498 | 0.465971 | 0.496699 |

The upper tail is compressed well below 0.55. Fold-3 and fold-4 do not cross 0.50 at all.

### Base-cost threshold sweep

| Threshold | fold-1 | fold-2 | fold-3 | fold-4 | Cross-fold verdict |
| --- | --- | --- | --- | --- | --- |
| 0.50 | 60 signals, -1.8624% avg | 9 signals, +2.8454% avg | 0 signals | 0 signals | REJECT: zero-signal + non-positive fold |
| 0.51 | 9 signals, -1.4613% avg | 2 signals, -13.4216% avg | 0 signals | 0 signals | REJECT: zero-signal + non-positive folds |
| 0.52 | 0 signals | 0 signals | 0 signals | 0 signals | REJECT: zero-signal |
| 0.53 | 0 signals | 0 signals | 0 signals | 0 signals | REJECT: zero-signal |
| 0.54 | 0 signals | 0 signals | 0 signals | 0 signals | REJECT: zero-signal |
| 0.55 | 0 signals | 0 signals | 0 signals | 0 signals | REJECT: zero-signal |

At 0.50 the selection rate is approximately 0.1866% in fold-1 and 0.0315% in fold-2, while fold-3 and fold-4 remain at 0%. At 0.51 the selection rate falls to approximately 0.0280% in fold-1 and 0.0070% in fold-2. Fold-2 at 0.51 contains only two signals and has `maximum_symbol_concentration = 1.0`, so it is not a robust candidate despite being an extreme upper-tail slice.

## Threshold conclusion

**No candidate threshold from 0.50 through 0.55 is supported across all four folds.**

Therefore this evidence does not justify changing the configured threshold from 0.55 to 0.50, 0.51, 0.52, 0.53 or 0.54. The threshold remains unchanged.

The observed pattern points beyond a simple threshold-setting problem:

1. predicted probabilities are concentrated below 0.50 in later folds;
2. the few fold-1 upper-tail signals remain negative after base costs;
3. fold-2 is unstable at the extreme tail and becomes fully symbol-concentrated at 0.51;
4. fold-1 still fails naive log loss independently of threshold selection.

The next model-quality question belongs in probability calibration, label prevalence/class separation, feature signal and fold/regime drift. That work requires a separate bounded diagnostic/retraining authority if it needs another governed dataset read.

## Diagnostic hardening added in PR #302

The threshold diagnostic code now records or supports:

- mean predicted probability;
- label positive rate;
- calibration gap;
- positive-label versus negative-label mean probability separation;
- count/rate above 0.50;
- per-threshold selection rate;
- explicit `ZERO_SIGNAL`, `POSITIVE_NET_RETURN` and `NON_POSITIVE_NET_RETURN` outcomes;
- cross-fold threshold verdicts;
- a fail-closed recommendation when no candidate threshold is supported across every fold.

These are diagnostic-only additions. They do not mutate `model_quality_gate`.

## Evidence receipt

The exact replay outcome is frozen in:

`research/receipts/2026-09-15-core100-threshold-sweep-replay-run-34936331199.json`

## Safety boundary

The completed diagnosis did not perform or authorize:

- threshold changes;
- model-quality gate changes;
- R2 writes;
- provider requests;
- holdout access;
- training publication during the replay;
- automatic model promotion;
- formal trade plans;
- real-money orders;
- live trading;
- source switching;
- Pionex-native relabeling.

Historical acquisition remains complete and must not be restarted solely because of this REJECT outcome.
