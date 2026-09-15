# Resource Hub Statistical Cross-check V0.1

Status: `PREPARED_RESEARCH_ONLY`

## Purpose

This harness follows the reviewed `anti-gambling-trader-tw` candidate evaluation without importing or executing upstream code.

It independently implements the documented IID centered-bootstrap mean semantic and compares it with Crypto Autopilot's existing stationary-bootstrap mean test. The comparison is useful because the reviewed upstream method assumes independent trade observations, while Crypto Autopilot's stationary bootstrap can preserve short-range serial dependence.

## Allowed inputs

Only:

- `synthetic_fixture`
- `existing_non_holdout_fixture`

Provider data, R2 material, frozen/replacement holdout data, broker data, or any unclassified input fail closed.

## Interpretation

Possible comparison states:

- `BOTH_SIGNIFICANT_RESEARCH_SIGNAL`
- `IID_ONLY_DIVERGENCE_SERIAL_DEPENDENCE_WARNING`
- `STATIONARY_ONLY_DIVERGENCE_REVIEW`
- `NOT_SIGNIFICANT`

Every result remains `DESCRIPTIVE_CROSSCHECK_ONLY`.

The harness is not:

- an upstream source-code equivalence proof;
- a formal strategy edge gate;
- a model-promotion signal;
- a replacement for deflated Sharpe, PBO/CSCV, Romano-Wolf, signal permutation, frozen validation, or holdout governance;
- a broker, execution, or trading component.

## Why this matters

A deterministic serial-dependence regression demonstrates the exact limitation the evaluation identified: an IID bootstrap can report a positive mean as significant while the stationary bootstrap does not. In that case the harness emits an explicit serial-dependence warning rather than promoting the result.

## Lineage

- Resource Hub candidate: `anti-gambling-trader-tw`
- Reviewed upstream commit: `9d938b64c80ee29363aed496ba4e61d9110a7222`
- Evaluation receipt: `research/receipts/2026-09-15-resource-hub-anti-gambling-trader-evaluation-v0-1.json`
- Prepared from Crypto Autopilot main: `1b97428b55833e2a36ca70cb43bbe156e4fc1fac`

All authority flags in `config/resource_hub_statistical_crosscheck_v0_1.json` remain false.
