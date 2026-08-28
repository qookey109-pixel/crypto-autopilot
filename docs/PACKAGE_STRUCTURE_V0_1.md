# Python Package Structure V0.1

Status: **EFFECTIVE ENGINEERING CONVENTION / NO AUTHORITY CHANGE**

## Purpose

Keep `src/crypto_autopilot/` navigable as the project grows without changing
strategy behavior, provider authority, cloud execution, frozen evidence or
paper/live-trading boundaries.

Before this structure was introduced, 69 Python files were placed directly in
the package root. The root now contains 24 files, including `__init__.py`.
Domain implementation lives in named subpackages; the remaining root modules
are explicit stable or version-bound exceptions.

## Domain packages

| Package | Responsibility |
| --- | --- |
| `binance/` | Binance research archives, coverage, capacity, catalogs and materialization helpers |
| `exchanges/` | Public/provider adapters and the Repository Paper Broker exchange boundary |
| `features/` | Technical, multi-timeframe, market-state and order-flow feature construction |
| `history/` | Historical admission, liquidity, replay, SState context and universe review |
| `paper/` | Paper-only exploration, deterministic simulation and candidate training |
| `providers/` | Provider comparison, forensics and prepared capture-suspension helpers |
| `research/` | Evaluation integrity, experiment registry, research context and signal governance |
| `storage/` | R2, Parquet, object layout, budget and ephemeral-output enforcement |
| `training/` | Online/detailed training, ablation, model quality and periodic review |

Package `__init__.py` files contain descriptions only. They do not re-export
domain APIs, so imports identify the owning module directly and do not create a
second hidden public surface.

## Root allowlist

Only the following Python files may remain immediately below
`src/crypto_autopilot/`.

### Stable cross-domain APIs

- `__init__.py`
- `backtest.py`
- `historical.py`
- `lineage.py`
- `models.py`
- `risk.py`
- `sstate_adapter.py`
- `sstate_evidence.py`
- `strategy.py`
- `technical.py`
- `universe.py`

These modules are high-fan-in interfaces used across multiple domains. Moving
them in the same change would add package churn without clarifying ownership.

### Versioned workflow or receipt-bound exceptions

- `binance_expansion_plan.py`
- `binance_funding.py`
- `binance_funding_budget.py`
- `binance_funding_materialization_plan.py`
- `binance_funding_materialization_plan_v0_2.py`
- `binance_historical.py`
- `provider_metadata_capture_v0_10.py`
- `provider_metadata_capture_v0_2.py`
- `provider_metadata_capture_v0_8.py`
- `provider_metadata_capture_v0_8_successor.py`
- `provider_metadata_stability_v0_11.py`
- `strategy_edge_validation.py`
- `strategy_research_loop.py`

These paths are named by workflows, frozen evidence or current versioned
governance. They stay in place until a separately reviewed version explicitly
changes those bindings. Their presence at the root is not a precedent for new
flat modules.

## Dependency rules

1. New domain code goes in the matching subpackage, not the root.
2. New or migrated cross-package imports use the full package path, for example
   `crypto_autopilot.features.advanced`.
3. Domain packages may depend on stable root APIs. Stable root APIs must not
   import domain packages merely to provide convenience re-exports.
4. Exchange, storage, strategy, risk and paper-broker boundaries remain
   separable. Package placement never grants a new authority.
5. Frozen receipts/configs are not rewritten to describe a later source-tree
   layout. Current documentation and executable imports point to the new paths;
   historical evidence remains historical.
6. Workflow/receipt-bound root exceptions may move only with a new versioned
   binding and regression coverage.

## Migration map

| Previous module | Current module |
| --- | --- |
| `advanced_technical` | `features.advanced` |
| `market_features` | `features.market` |
| `market_structure` | `features.structure` |
| `multi_timeframe_technical` | `features.multi_timeframe` |
| `orderflow` | `features.orderflow` |
| `detailed_history` | `history.detailed` |
| `historical_admission` | `history.admission` |
| `historical_liquidity` | `history.liquidity` |
| `historical_sstate` | `history.sstate` |
| `historical_universe` | `history.universe` |
| `historical_universe_review` | `history.universe_review` |
| `replay_readiness` | `history.replay_readiness` |
| `paper_exploration` | `paper.exploration` |
| `paper_simulation_demo` | `paper.simulation_demo` |
| `paper_training` | `paper.training` |
| `detailed_training` | `training.detailed` |
| `monthly_universe_review` | `training.monthly_universe_review` |
| `online_r2_training` | `training.online_r2` |
| `online_training` | `training.online` |
| `shadow_ablation` | `training.shadow_ablation` |
| `training_quality` | `training.quality` |
| `weekly_model_review` | `training.weekly_review` |
| `evaluation_integrity` | `research.evaluation_integrity` |
| `experiment_registry` | `research.experiment_registry` |
| `parameter_sweep` | `research.parameter_sweep` |
| `pilot_evidence` | `research.pilot_evidence` |
| `research_automation_health` | `research.automation_health` |
| `research_context` | `research.context` |
| `research_signal_ingest_v0_2` | `research.signal_ingest_v0_2` |
| `research_signal_layer` | `research.signal_layer` |
| `research_signal_quality` | `research.signal_quality` |
| `resource_planning` | `research.resource_planning` |
| `binance_2025_pilot` | `binance.pilot_2025` |
| `binance_capacity` | `binance.capacity` |
| `binance_coverage` | `binance.coverage` |
| `binance_funding_coverage` | `binance.funding_coverage` |
| `binance_funding_materializer_v0_2` | `binance.funding_materializer_v0_2` |
| `binance_spot_history` | `binance.spot_history` |
| `binance_training_catalog` | `binance.training_catalog` |
| `binance_vision` | `binance.vision` |
| `equivalence_forensics` | `providers.equivalence_forensics` |
| `provider_equivalence` | `providers.equivalence` |
| `provider_metadata_capture_suspension_v0_2` | `providers.metadata_capture_suspension_v0_2` |
| `ephemeral_storage` | `storage.ephemeral` |
| `r2_budget` | `storage.budget` |

## Explicit non-goals

- No strategy, risk, portfolio or execution behavior changed.
- No provider call, R2 access, holdout access, model promotion or order path was
  added or run.
- No frozen receipt/config or V0.10/V0.11 workflow binding was changed.
- `scripts/` and `tests/` remain flat executable/test suites in this migration;
  many script names are workflow-facing entry points. They can be grouped only
  after their workflow and evidence bindings are separately inventoried.

The largest remaining internal module is `training/quality.py`. Its size is a
separate cohesion concern; splitting it safely requires behavior-level tests
around its internal responsibilities and is intentionally not combined with
this path-only migration.
