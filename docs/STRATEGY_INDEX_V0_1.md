# Strategy Index V0.1

The project has one Paper baseline and several non-authoritative research layers.
They are not interchangeable and are not added together into an invented score.

| Layer | Source | Current state | Purpose |
| --- | --- | --- | --- |
| Paper baseline | `config/strategy_v0_1.json` | PAPER / LONG_ONLY | SState admission, 100-point entry quality, structural risk and exits |
| Paper successor | `config/post_window_paper_training_v0_2.json` | PREPARED_WAITING_FOR_HOLDOUT_AUTHORITY | resume current-market simulation with the existing broker after the scientific access gates are satisfied |
| Technical analysis | `config/technical_analysis_v0_2.json` | RESEARCH_ONLY | causal 4H/60M/15M indicators and market structure |
| Shadow ablation | `config/binance_spot_shadow_v0_6.json` | PREPARED_NOT_ACTIVE | compare eight feature groups without automatic promotion |
| Research loop | `config/strategy_research_loop_v0_1.json` | PREPARED_RESEARCH_ONLY | 120 preregistered candidates over four families and three horizons |
| Edge validation | `config/strategy_edge_validation_v0_1.json` | PREPARED_RESEARCH_ONLY | six anti-overfitting and disjoint-validation methods |
| Parameter sweep | `config/strategy_parameter_sweep_v0_1.json` | FRAMEWORK_ONLY | protocol only; candidate values and split are still undefined |
| TradingAgents challenger | `config/tradingagents_research_challenger_v0_1.json` | PREPARED_RESEARCH_ONLY | normalize point-in-time multi-agent research as descriptive context; no upstream execution or trading authority |
| Daily Opportunity Engine | `config/daily_opportunity_engine_v0_1.json` | PREPARED_RESEARCH_ONLY | multi-asset attention selector; DIRECTIONAL and RANGE_EXTREMITY profiles; may return NO_CANDIDATE |
| Strategy Router | `config/strategy_router_v0_1.json` | PREPARED_RESEARCH_ONLY | map one selected asset to zero or more compatible strategy families or NO_TRADE |
| Multi-Strategy Library | `config/strategy_library_v0_1.json` | PREPARED_RESEARCH_ONLY | canonical six-family registry and lifecycle/authority metadata used by Strategy Router |
| Strategy Family Validation | `config/strategy_family_validation_v0_1.json` | PREPARED_RESEARCH_ONLY | aggregate existing Edge PASS evidence into cross-asset/cross-regime family generalization review without ranking or promotion |
| Strategy Research Scorecard / Ranking | `config/strategy_research_scorecard_v0_1.json` | PREPARED_RESEARCH_RANKING_ONLY | rank governed family evidence for research-review priority only; no winner selection, automatic strategy selection, sizing or execution authority |
| Risk / Position Sizing | `config/risk_position_sizing_v0_1.json` | PREPARED_RESEARCH_ONLY | preserve upstream stop, separate target vs realized risk, and bound notional by leverage/notional constraints without order authority |
| Portfolio Admission | `config/portfolio_admission_v0_1.json` | PREPARED_RESEARCH_PAPER_ONLY | evaluate explicit multi-asset/multi-strategy baskets against total-risk, concentration, overlap and gross-notional gates without ranking or subset optimization |
| Paper Execution | `config/paper_execution_v0_1.json` | PREPARED_PAPER_ONLY | bind validated family lineage and approved risk notional into deterministic idempotent Repository Paper Broker LONG intents; no automatic/live execution |
| Paper Fill / Order Lifecycle | `config/paper_fill_lifecycle_v0_1.json` | PREPARED_PAPER_SIMULATION_ONLY | simulate causal LONG fills, partial fills, slippage, fees and stop/target lifecycle from accepted paper intents; normalized liquidity only, no live execution |
| Paper Account / Position State | `config/paper_account_state_v0_1.json` | PREPARED_PAPER_STATE_ONLY | rebuild immutable cash/equity/open-position state from lifecycle evidence and marks; export current open exposure back to Portfolio Admission |
| Paper Cycle Orchestrator | `config/paper_cycle_orchestrator_v0_1.json` | PREPARED_MANUAL_CYCLE_ONLY | rebuild current account context, evaluate one explicit basket, and prepare all-or-none paper intents without broker submission or lifecycle execution |
| Paper Submission Session | `config/paper_submission_session_v0_1.json` | PREPARED_EXPLICIT_PAPER_SUBMISSION_ONLY | require exact cycle-id confirmation and complete-basket preflight before idempotent in-memory PaperBroker submission; no scheduling/persistence/live path |
| Paper Lifecycle Batch | `config/paper_lifecycle_batch_v0_1.json` | PREPARED_EXPLICIT_PAPER_LIFECYCLE_BATCH_ONLY | require exact session-id confirmation and complete accepted-basket lifecycle inputs; reuse existing Lifecycle engine and emit Account-ready records without provider/persistence/live path |
| Paper Account Advance | `config/paper_account_advance_v0_1.json` | PREPARED_EXPLICIT_ACCOUNT_REMATERIALIZATION_ONLY | require exact batch-id confirmation, replace latest lifecycle record by intent, rematerialize account, and emit next account input without persistence/live path |
| Paper Loop Checkpoint | `config/paper_loop_checkpoint_v0_1.json` | PREPARED_PORTABLE_HANDOFF_ONLY | require exact advance-id confirmation, rematerialize next account, reconcile exposure and package deterministic next-cycle handoff without persistence/live path |
| Paper Loop Resume | `config/paper_loop_resume_v0_1.json` | PREPARED_EXPLICIT_MANUAL_RESUME_ONLY | require exact checkpoint-id confirmation, validate account/policy/exposure lineage and reuse the existing Paper Cycle engine without submission/persistence/live path |
| Paper Loop Integrity / Multi-Cycle Replay | `config/paper_loop_integrity_v0_1.json` | PREPARED_AUDIT_ONLY | audit 2–8 complete forward rounds, recompute all stage ids, require exact Checkpoint chaining and deterministic transcript replay without executing or ranking strategies |
| Paper Loop Run Package / Transcript | `config/paper_loop_run_package_v0_1.json` | PREPARED_PORTABLE_AUDIT_PACKAGE_ONLY | re-audit Integrity transcript, bind complete proof/stage manifest/terminal Checkpoint into deterministic portable JSON; package is not execution authority |
| Paper Run Package Artifact Export | `config/paper_run_package_artifact_export_v0_1.json` | PREPARED_SECONDARY_AUDIT_EXPORT_ONLY | re-verify a Run Package and prepare canonical package/manifest/SHA evidence for manual GitHub Artifact upload; Artifact never becomes execution authority |
| Live Paper Simulation | `config/live_paper_simulation_v0_1.json` | PREPARED_LIVE_PAPER_SIMULATION | allow public Pionex market data and tick-by-tick paper lifecycle/account/checkpoint progress; private API, real-money orders and real live trading remain false |
| Live Paper Run Coordinator | `config/live_paper_run_coordinator_v0_1.json` | PREPARED_EXPLICIT_PERSISTENT_COORDINATION_ONLY | chain verified Live Paper ticks into restartable append-only run steps and committed-request replay; manual-only, no auto candidate/Scorecard selection, no real orders |
| Paper Run Store | `config/paper_run_store_v0_1.json` | PREPARED_PAPER_EVIDENCE_PERSISTENCE | persist deterministic paper state/evidence through Local JSON or existing Cloudflare R2 adapter; stored objects never become execution authority |

## Analysis flow

```text
SState context gate
        ↓
technical entry-quality gate
        ↓
Repository Paper evidence
        ↓
research registry + Edge checks + family validation
        ↓
research Scorecard / priority ranking
        ↓
cost/risk audit + human review eligibility only
```

The dashboard strategy page is generated by
`scripts/build_strategy_projection.py`. It reads the governed projection inputs
for that surface and fails closed if provider, R2, holdout, promotion or trading
authority appears. The product-stage selector/library/validation contracts above
are separate research architecture and are not silently added to the dashboard
entry score.
The checked-in `web/data/strategy.json` is a fixture with `authority=false`;
Pages rebuilds it during deployment.

No strategy parameter, SHORT score, model-promotion rule or live authority is
changed by this index. The Paper successor is an execution-readiness contract,
not a seventh score or a strategy promotion.

The TradingAgents challenger is also not a new strategy score. Its upstream
rating and report hashes may be evaluated only as comparable research evidence;
they cannot replace the canonical strategy, Risk Engine or Paper Broker.

The product-stage Daily Opportunity Engine, Strategy Router, Multi-Strategy
Library and Risk / Position Sizing layer are selectors/registries/planners rather
than additional entry-score components.
Their outputs must not be added to the Paper baseline score. Router family names
come from the governed strategy library registry, and a family remains
research-only until separate multi-asset/generalization evidence supports a
later lifecycle transition.
