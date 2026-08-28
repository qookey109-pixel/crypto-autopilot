# Strategy Edge Validation V0.1

Status: **PREPARED RESEARCH-ONLY / PRODUCTION DATA EXECUTION NOT AUTHORIZED**

## Outcome

This layer rejects Challenger results that are statistically fragile after
parameter search. It complements, rather than replaces, the existing causal
backtest, walk-forward, fee/slippage, drawdown and exposure checks.

The layer is deterministic, standard-library only and emits one JSON report.
It performs no provider request, R2 operation, holdout access, model promotion,
trade-plan generation or order operation.

## Position in the research funnel

```text
lineage and data integrity
  -> causal/no-lookahead replay
  -> fee, slippage, drawdown and exposure gates
  -> UPDATE-only parameter selection and local-neighbor stability
  -> Strategy Edge Validation V0.1
  -> disjoint paper/shadow evidence
  -> human review only
```

A `PASS` means only `EDGE_EVIDENCE_READY_FOR_HUMAN_REVIEW`. It never changes a
strategy, promotes a model or grants trading authority.

## Required evidence

The input contract contains two deliberately separate partitions:

- a complete candidate return matrix from `UPDATE` evidence;
- one already-selected candidate's returns from disjoint `VALIDATION` evidence.

It also requires:

- the exact ordered candidate/experiment IDs;
- a complete immutable trial-registry claim and SHA-256;
- an upstream disjoint-partition integrity PASS and its SHA-256;
- aligned update and validation benchmarks;
- aligned validation market returns and positions for signal-timing permutation;
- explicit provider identity;
- all access/authority flags set to false.

Missing trials are not treated as a smaller search. A missing, partial,
misaligned, non-finite or zero-variance input fails closed. The frozen
replacement holdout is not an accepted input role.

## Frozen gates

### Stationary bootstrap

The selected candidate's disjoint validation excess-return mean is tested with
a deterministic stationary bootstrap. Blocks preserve short-range serial
dependence better than independent row resampling.

### Deflated Sharpe Ratio

The selected UPDATE Sharpe is compared with the expected maximum across every
registered trial, with skewness and kurtosis in the sampling adjustment. Trial
count and dispersion therefore penalize broad parameter searches.

### PBO / CSCV

The complete UPDATE return matrix is divided into eight contiguous partitions.
Every symmetric four-partition split selects the in-sample winner and measures
its out-of-sample rank. The Probability of Backtest Overfitting must be no more
than the frozen threshold.

### Romano-Wolf stepdown

All candidates are compared with the same aligned benchmark using a joint
stationary bootstrap. Stepdown-adjusted p-values preserve cross-candidate
dependence and control family-wise false positives more efficiently than
testing each candidate independently. The selected candidate and the global
max-t gate must both pass.

### Disjoint validation retention

The already-selected candidate must retain a positive excess Sharpe on the
disjoint validation partition and retain at least the frozen fraction of its
UPDATE Sharpe. Validation is never used to select another candidate.

### Signal-alignment permutation

Validation positions are circularly shifted against validation market returns.
This preserves each sequence while destroying their original time alignment.
It tests whether signal timing contributes information. It does not reproduce
path-dependent stop/target execution, which remains a documented limitation.

## Deliberate non-combination

This layer does not recalculate or hide:

- exchange fees or slippage;
- market capacity;
- funding;
- maximum drawdown;
- symbol and direction exposure;
- same-bar stop/target collision rules;
- causal feature or next-bar execution rules.

Those remain separate upstream evidence. Statistical significance cannot
rescue a candidate that fails cost, drawdown, exposure or causal-integrity
gates.

## CLI

The CLI reads explicit files and prints JSON to stdout. It has no output-file,
network or cloud-storage path.

```bash
PYTHONPATH=src python scripts/validate_strategy_edge.py \
  --input /tmp/edge-input.json \
  --config config/strategy_edge_validation_v0_1.json
```

Exit status is `0` for `PASS` and `2` for `REJECT`, including malformed input.

## Research basis

- Politis, D. N. and Romano, J. P. (1994), *The Stationary Bootstrap*,
  doi:10.1080/01621459.1994.10476870.
- Bailey, D. H. and López de Prado, M. (2014), *The Deflated Sharpe Ratio:
  Correcting for Selection Bias, Backtest Overfitting and Non-Normality*,
  SSRN 2460551.
- Bailey, D. H., Borwein, J. M., López de Prado, M. and Zhu, Q. J. (2017),
  *The Probability of Backtest Overfitting*, doi:10.21314/JCF.2016.322.
- Hansen, P. R. (2005), *A Test for Superior Predictive Ability*,
  doi:10.1198/073500105000000063.
- Romano, J. P. and Wolf, M. (2005), *Stepwise Multiple Testing as Formalized
  Data Snooping*, doi:10.1111/j.1468-0262.2005.00615.x.

V0.1 uses a studentized global max-t result from the same stationary-bootstrap
family used by the Romano-Wolf implementation as the conservative global
superior-predictive-ability gate. It does not claim to reproduce every
lower/consistent/upper p-value variant of Hansen's reference implementation.

## Current authority boundary

- V0.10 workflow and frozen evidence: unchanged.
- SState core: unchanged.
- Production dataset execution: not authorized.
- R2 list/read/write: not authorized.
- Replacement holdout: `FROZEN_UNOPENED`.
- Model promotion: human-review eligibility only, no authority.
- Trade plan, real-money order and live trading: unauthorized.
