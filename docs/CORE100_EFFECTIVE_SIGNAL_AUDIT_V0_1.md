# Core100 Effective Signal Audit V0.1

Status: `AUTHORIZED_ONE_SHOT_AFTER_REVIEWED_MAIN_MERGE`

## Purpose

This audit diagnoses why the completed Binance USD-M Crypto Core 100 research training reached a model-quality `REJECT` without changing the model, threshold, provider, strategy, or trading authority.

It rebuilds the exact governed training examples from the existing completed R2 dataset using the same partition SHA validation, history-quality validation, causal multi-timeframe feature builder, per-symbol bounding, and global bounding used by the training path.

The audit does **not** call the model optimizer and does **not** call the R2 training publication path.

## Frozen lineage

The one-shot run fails closed unless all of these remain exact:

- dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`
- partition objects: `14,274`
- source rows: `18,235,427`
- bounded examples: `249,228`
- symbols: `100`
- source end exclusive: `2026-08-01T00:00:00Z`
- replacement holdout starts: `2026-08-28T00:00:00Z`

The replacement holdout stays closed.

## Diagnostics

The output contains aggregate statistics only:

1. global and per-fold label balance;
2. actual same-symbol spacing and the observed fraction of adjacent bounded examples whose four-hour label windows overlap;
3. timestamp clustering across symbols, so cross-sectional same-time concentration is visible;
4. per-fold symbol positive-rate drift, bounded to the largest aggregate changes;
5. per-fold technical regime drift using only existing features:
   - trend: sign of `ema20_vs_ema50_1h`;
   - volatility: low/mid/high buckets of `atr_percentile_1h`;
6. positive-vs-negative standardized feature separation in each test fold;
7. train-vs-test standardized feature drift;
8. high feature-correlation pairs on a deterministic bounded sample.

The dependence section is descriptive. It deliberately does not claim a formal effective sample size or IID-adjusted confidence level.

## Why actual overlap is measured

The raw example builder considers a sample every four 15-minute bars and labels the next sixteen 15-minute bars. However, the final training set is deterministically bounded to at most 2,500 examples per symbol across the four-year source window.

Therefore it is not scientifically valid to infer that the final 249,228 examples are heavily label-overlapped merely from the raw one-hour candidate stride. V0.1 measures the spacing of the final bounded examples directly.

## Execution boundary

The workflow has no schedule and no `workflow_dispatch`. It can run only on the protected-main push that first introduces the exact authority receipt. The receipt explicitly does not grant merge authority.

Allowed operation:

- existing governed production R2 training reads inside GitHub Actions.

Forbidden operations:

- provider requests;
- R2 writes;
- replacement holdout access;
- model fitting or retraining;
- model/training publication;
- threshold or strategy changes;
- source switching;
- model promotion;
- formal trade plans;
- real-money orders;
- live trading.

The only persistent output from the audit is a secret-free aggregate GitHub Actions artifact retained for 90 days.

## Interpretation

The report is designed to distinguish several competing explanations for the current rejection:

- label/prevalence drift;
- market-regime drift;
- symbol-specific drift;
- weak or decaying technical-feature separation;
- redundant technical features;
- dependence caused by overlapping same-symbol labels or synchronized cross-sectional timestamps;
- a later need to benchmark nonlinear model capacity.

No threshold should be changed merely because this audit exists. A model-capacity experiment should be considered only after the information and drift diagnostics are read.
