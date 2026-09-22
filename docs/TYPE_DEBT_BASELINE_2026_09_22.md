# Type Debt Baseline V0.1 — 2026-09-22

Repository `main` remains authority. This document records the first measured non-blocking mypy baseline after PR #427; it is not a required gate and grants no execution authority.

Evidence:

- reviewed parent main: `9ffe30c8f0ab28bc3b2a95ae19de6938ed613dae`;
- CI run: `35685558516`;
- artifact: `10676955738` / `quality-visibility-35685558516-1`;
- mypy: `2.3.1`;
- Python target: `3.13`;
- scan target: `src/crypto_autopilot`.

## Baseline

- 465 total diagnostics;
- 261 errors;
- 204 notes;
- 49 files with at least one error;
- baseline clean: **false**.

Error-code distribution:

- `arg-type`: 111
- `call-overload`: 63
- `attr-defined`: 41
- `operator`: 20
- `index`: 13
- `assignment`: 5
- `union-attr`: 5
- `misc`: 1
- `no-redef`: 1
- `return-value`: 1

The top three families account for **215 / 261 errors (82.38%)**. The dominant pattern is not hundreds of unrelated bugs; it is dynamic values typed as `object` reaching conversion, mapping, and attribute boundaries without explicit narrowing.

## Highest-count files

1. `binance_expansion_plan.py` — 17
2. `portfolio/admission_v0_1.py` — 16
3. `paper/live_v0_1.py` — 14
4. `binance_funding_materialization_plan_v0_2.py` — 13
5. `history/pionex_reach_v0_3.py` — 13
6. `toolkit/descriptive_context_v0_1.py` — 13
7. `binance/funding_coverage.py` — 12
8. `features/advanced.py` — 12
9. `research/pionex_universe_v0_1.py` — 12
10. `binance_funding_materialization_plan.py` — 11
11. `research/strategy_scorecard_v0_1.py` — 11
12. `binance_funding_budget.py` — 10
13. `training/detailed.py` — 10

## Remediation order

First lane: non-execution dynamic-object narrowing with characterization tests.

Initial review candidates:

- `toolkit/descriptive_context_v0_1.py`
- `research/pionex_universe_v0_1.py`
- `research/strategy_scorecard_v0_1.py`
- `binance_expansion_plan.py`
- `binance_funding_budget.py`

Execution-sensitive paper paths are deliberately deferred from the first type-debt batch:

- `paper/live_v0_1.py`
- `paper/run_coordinator_v0_1.py`
- `paper/run_recovery_v0_1.py`

## Rules for reducing the baseline

Do not reduce the count by broadening values to blanket `Any`, adding blanket `# type: ignore`, or changing behavior solely to satisfy mypy. Prefer explicit narrowing, validated parsing boundaries, TypedDict/dataclass contracts where appropriate, and characterization tests before touching behavior-bearing code.

The mypy report remains informational. No error threshold becomes a merge, promotion, holdout, provider, source-switch, order, or trading gate from this baseline.
