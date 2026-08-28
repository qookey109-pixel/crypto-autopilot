# Strategy Parameter Freeze / Sweep Framework V0.1

## Purpose

Define how currently `UNDEFINED` SState Intraday Wave V0.1 strategy rules may eventually become versioned parameters without tuning directly against validation results.

This framework is an anti-overfitting control plane. It does **not** freeze any production strategy parameter values and it does **not** authorize automatic historical trade-plan generation.

## Current authority boundary

The current strategy authority leaves these rules undefined:

1. ATR-normalized maximum 1H extension from EMA20.
2. 15m pullback proximity/semantics around EMA20.
3. 15m EMA20 reclaim semantics.
4. Previous-high break semantics.
5. Volume-confirmation threshold/semantics.
6. Structural-stop ATR buffer size.

Some rules may ultimately be numeric; others may require categorical semantic variants. The sweep framework therefore supports both ordered numeric and categorical candidate axes.

No candidate values for the six rules above are frozen by this document.

## Core protocol

### 1. Freeze the plan before evaluation

A `SweepPlan` freezes:

- plan id;
- ordered parameter axes and all candidate values;
- UPDATE fold ids;
- one disjoint VALIDATION fold id;
- primary metric;
- minimum trade-count gates;
- update and validation metric floors;
- update and validation drawdown ceilings;
- local-neighbor stability requirements.

A SHA-256 plan fingerprint changes if any of those values change.

Candidate grids are deterministic Cartesian products and are capped at 4,096 candidates to prevent accidental combinatorial explosions.

### 2. UPDATE-only selection

Candidate selection accepts `UPDATE` observations only.

The full candidate × UPDATE-fold matrix is mandatory. Selectively omitting weak candidate/fold results is a protocol error.

A candidate is update-eligible only if every update fold passes the frozen:

- minimum trade count;
- primary-metric floor;
- maximum drawdown.

Among eligible candidates, ranking is deterministic and robust-first:

1. highest worst-fold primary metric;
2. highest median primary metric;
3. lower worst-fold drawdown;
4. deterministic candidate id.

Validation data is not accepted by this selection function.

### 3. Local sensitivity / stability gate

The update-selected candidate must not be a narrow isolated peak.

A neighbor is a candidate differing by exactly one adjacent value on one frozen axis. The selected candidate must have at least the frozen minimum number of eligible neighbors whose worst-fold primary metric is no more than the frozen allowed drop below the selected candidate.

The framework does not prescribe the final neighbor-count or allowed-drop values. Those values themselves must be frozen in the sweep plan before evaluation.

### 4. One-candidate validation

Validation receives only the candidate already selected from UPDATE.

The validation function rejects:

- a different candidate id;
- an UPDATE observation passed as validation;
- a validation fold that differs from the frozen plan;
- a selection produced under a different plan fingerprint.

Validation therefore cannot be used to rank alternatives or switch to the second-best candidate after seeing the result.

The validation decision is `PASS` or `FAIL` and marks `validation_consumed = true`.

Operationally, the validation decision/receipt must be persisted by the workflow or Repository authority. A failed validation is evidence, not permission to silently revise the grid and reuse the same holdout.

### 5. Freeze only after PASS

`freeze_validated_parameters(...)` succeeds only when:

- the validation decision is PASS;
- the plan fingerprints match;
- the validation candidate is exactly the UPDATE-selected candidate.

The frozen result records:

- exact parameter values;
- plan fingerprint;
- digest of the complete UPDATE observation matrix;
- validation fold id;
- validation evidence reference;
- validation metric/trade-count/drawdown evidence.

Parameter-freeze PASS is necessary but no longer sufficient for Challenger
promotion review. When a complete aligned return matrix exists, the selected
candidate must also pass the separately versioned `Strategy Edge Validation
V0.1` statistical gates. That layer consumes the complete trial family, never
reselects on validation and grants zero automatic promotion authority. See
`docs/STRATEGY_EDGE_VALIDATION_V0_1.md`.

## Primary metrics

V0.1 framework supports:

- `mean_r`;
- `return_pct`.

The production sweep plan must choose one before evaluation. The framework intentionally has no default primary metric.

Profitability is not assumed. A positive update result is not a claim that validation or future paper trading will pass.

## Relationship to existing project layers

```text
Historical candles / R2
        ↓
Historical Universe
        ↓
Technical Features
        ↓
Historical SState Replay
        ↓
Strategy Replay Readiness
        ↓
Parameter Freeze / Sweep Framework
        ↓
(future frozen parameters)
        ↓
Automatic historical plan generation
        ↓
Backtest Engine
```

`Strategy Replay Readiness` remains the authority for whether a historical trade plan may be generated. Until the required rule semantics/parameters have passed this process and are integrated into a versioned strategy authority, `trade_plan_authorized` remains false.

## Anti-overfitting rules

The following are prohibited by this framework:

- choosing candidate values after inspecting validation;
- removing bad update folds from the matrix;
- selecting based on validation rank;
- switching candidates after a validation failure;
- freezing an isolated update peak that fails the local-stability gate;
- changing the candidate grid without changing the plan fingerprint;
- treating a test fixture as historical strategy evidence;
- claiming a parameter is authoritative merely because it maximizes one backtest sample.

## Not yet frozen

This framework does not yet define:

- real candidate values for the six undefined strategy rules;
- the real UPDATE/VALIDATION time split;
- the production primary metric;
- production trade-count/drawdown gates;
- production local-stability tolerances;
- a real historical SState evidence dataset;
- a validated parameter set.

Those remain future evidence work and must be frozen before the corresponding data is consumed.

## Safety

- Research/backtest only.
- No SState core modification.
- No private Pionex API.
- No live orders.
- No live-trading authorization.
