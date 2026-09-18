# Qookey Crypto Autopilot

Cloud-first, exchange-agnostic crypto trading research and automation platform.

> **Current mode: PAPER / LIVE-PAPER ONLY.** Public live market data, simulated live paper execution and paper-state persistence may be authorized by their versioned contracts; private exchange APIs, real-money orders and real live trading remain closed.

## Product architecture priority

Qookey Crypto Autopilot is multi-asset and opportunity-first, not a single-coin strategy project.

1. Daily Opportunity Engine — find the best current research/trading candidates from the governed universe, including the valid outcome of no trade.
2. Strategy Router — match each candidate to an evidence-supported strategy/regime or return `NO_TRADE`.
3. Risk / Position Sizing — separate market-driven stop distance from account-risk budgeting.
4. Portfolio Admission — apply total-risk, concentration and strategy-overlap gates to an explicit basket.
5. Automated Execution — deterministic paper cycle preparation, explicit intent submission, fill/lifecycle simulation and paper account state; only later live-capable execution under separate authority.
6. Post-trade Learning — feed outcomes back into research without silently promoting strategy authority.

See [`docs/PRODUCT_ARCHITECTURE_V0_1.md`](docs/PRODUCT_ARCHITECTURE_V0_1.md), [`docs/DAILY_OPPORTUNITY_ENGINE_V0_1.md`](docs/DAILY_OPPORTUNITY_ENGINE_V0_1.md), [`docs/STRATEGY_ROUTER_V0_1.md`](docs/STRATEGY_ROUTER_V0_1.md), [`docs/STRATEGY_LIBRARY_V0_1.md`](docs/STRATEGY_LIBRARY_V0_1.md), [`docs/STRATEGY_FAMILY_VALIDATION_V0_1.md`](docs/STRATEGY_FAMILY_VALIDATION_V0_1.md), [`docs/RISK_POSITION_SIZING_V0_1.md`](docs/RISK_POSITION_SIZING_V0_1.md), [`docs/PORTFOLIO_ADMISSION_V0_1.md`](docs/PORTFOLIO_ADMISSION_V0_1.md), [`docs/PAPER_EXECUTION_V0_1.md`](docs/PAPER_EXECUTION_V0_1.md), [`docs/PAPER_FILL_ORDER_LIFECYCLE_V0_1.md`](docs/PAPER_FILL_ORDER_LIFECYCLE_V0_1.md), [`docs/PAPER_ACCOUNT_POSITION_STATE_V0_1.md`](docs/PAPER_ACCOUNT_POSITION_STATE_V0_1.md), [`docs/PAPER_CYCLE_ORCHESTRATOR_V0_1.md`](docs/PAPER_CYCLE_ORCHESTRATOR_V0_1.md), [`docs/PAPER_SUBMISSION_SESSION_V0_1.md`](docs/PAPER_SUBMISSION_SESSION_V0_1.md), [`docs/PAPER_LIFECYCLE_BATCH_V0_1.md`](docs/PAPER_LIFECYCLE_BATCH_V0_1.md), [`docs/PAPER_ACCOUNT_ADVANCE_V0_1.md`](docs/PAPER_ACCOUNT_ADVANCE_V0_1.md), [`docs/PAPER_LOOP_CHECKPOINT_V0_1.md`](docs/PAPER_LOOP_CHECKPOINT_V0_1.md), [`docs/PAPER_LOOP_RESUME_V0_1.md`](docs/PAPER_LOOP_RESUME_V0_1.md), [`docs/PAPER_LOOP_INTEGRITY_V0_1.md`](docs/PAPER_LOOP_INTEGRITY_V0_1.md), [`docs/PAPER_LOOP_RUN_PACKAGE_V0_1.md`](docs/PAPER_LOOP_RUN_PACKAGE_V0_1.md), [`docs/LIVE_PAPER_SIMULATION_V0_1.md`](docs/LIVE_PAPER_SIMULATION_V0_1.md), and [`docs/PAPER_RUN_STORE_V0_1.md`](docs/PAPER_RUN_STORE_V0_1.md).

## Start here

For current work, read in this order:

1. [`CURRENT_STATUS.md`](CURRENT_STATUS.md) — concise current operations state.
2. [`research/status/current-operations-v0-3.json`](research/status/current-operations-v0-3.json) — machine-readable current-operations companion.
3. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — project-stage, governance, compatibility and retired-workflow index.
4. [`AGENTS.md`](AGENTS.md) — execution and safety rules for coding agents.
5. The exact versioned config, receipt, and immutable run evidence for the stage being changed.

Repository `main` is the formal current authority and must be resolved live at read time. Current Operations V0.3 intentionally does **not** claim that its stored evidence-basis SHA is the latest `main`; that SHA records the reviewed parent used to prepare the status version.

## Current Core100 state — 2026-09-16

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

- Detailed Core100 History acquisition is complete: `10/10` governed shards.
- Source training run: `34918219864` — workflow `success`, report `PASS`.
- Dataset: 100 symbols, 14,274 partition objects, 18,235,427 rows, 249,228 examples.
- Dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
- Model quality gate: **REJECT**; automatic promotion remains disabled.
- Exact read-only threshold replay run `34936331199` completed successfully.
- Evaluated thresholds: `0.50` through `0.55`.
- `supported_thresholds=[]` and `threshold_change_supported=false`.
- Configured threshold remains unchanged.

Do **not** restart the completed History program solely because model quality rejected, and do not loosen the quality gate merely because a diagnostic delta is small.

## Current Pionex validation state

PR #321 merged the narrow bounds-only invalid-OHLC provider-boundary behavior without correcting, fabricating, interpolating, or provider-splicing candles.

The current validation workflow is `.github/workflows/pionex-validation-materialization-v0-1.yml` and remains manual-only. The previous authorized run `34991627998` failed closed before the PR #321 fix. A new materialization must be dispatched from the Repository's **live `main` at dispatch time** before Repository-current Pionex validation can be called complete.

Still closed:

- private API / account data;
- replacement holdout access;
- training on the Pionex validation dataset;
- source switching;
- automatic model promotion;
- formal trade plans;
- real-money orders;
- live trading.

## Technical-debt cleanup

PR #322 merged the first control-plane convergence batch and established current-state entrypoints, root-doc/security convergence, current-main PR triage, and schedule-health inventory derivation.

The active cleanup is now the projection layer:

- prevent Current Status from becoming stale through self-referential latest-main SHA claims;
- build frozen/historical Dashboard authority first, then apply Current Operations V0.3 last;
- stop the homepage generator from restoring September 13 `8/10 / Training skipped / PR #292` text;
- keep V0.12 historical lineage while closing its expired present-tense execution flags;
- add broader non-blocking quality/security/dependency visibility only after the control plane is stable.

Cleanup register: [`docs/TECH_DEBT_REGISTER_2026_09_16.md`](docs/TECH_DEBT_REGISTER_2026_09_16.md).

## Current research components

### Qookey Crypto Toolkit V0.2

Merged research-only cloud commands cover capabilities, validation, indicators, strategy, risk, backtest, stress, compare, and report. Provider/R2 access, holdout access, automatic strategy mutation, model promotion, formal trade plans, real-money orders, and live trading remain disabled unless separately versioned and authorized.

### TradingAgents Research Challenger V0.1

Merged as `PREPARED_RESEARCH_ONLY`. It is an offline, non-authoritative research-context adapter and grants no upstream LLM/provider call, R2 operation, holdout access, strategy/risk mutation, trade plan, or order authority.

## Safety boundaries

- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- `source_switch_authorized=false` remains binding.
- Pionex-native and Binance USD-M evidence must remain provenance-separated.
- Project cloud/runtime budget remains **0 USD/month** for the FREE-ONLY path.
- Render must never receive R2 credentials.
- Secrets must never be committed, logged, artifacted, or pasted into chat.
- Frozen configs/receipts/evidence are immutable; create a new version instead of rewriting history.

## Historical authority lineage compatibility

The project preserves these frozen lineage names because fail-closed authority tests and historical evidence depend on them:

- **V0.8** remains HISTORICAL prepared/cutover evidence only.
- **V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE** remains historical effective authority; its GitHub-hosted schedule is retired.
- **V0.12 SUCCESSOR METADATA WINDOW** remains the successor metadata-only window lineage. Its bounded window is historical; the label does not mean it is the current active schedule today.
- **Equivalence V0.1** remains a definitive FAIL and must not be regraded by changing scope or thresholds.
- Replacement holdout remains **FROZEN_UNOPENED**.

These labels preserve governance lineage; they do not reopen provider access, holdout access, model promotion, source switching, or trading authority.

## Agent change walkthrough

The repository keeps one read-only change-inspection skill at `.agents/skills/change-walkthrough/SKILL.md`. It traces repository authority, base/head SHAs, local diff and test evidence around one canonical Python domain action. A walkthrough is evidence/navigation only and does not justify a second runtime, new execution path, merge approval, or execution authority.

## Useful entrypoints

- [`docs/PROJECT_MAP_V0_1.md`](docs/PROJECT_MAP_V0_1.md) — repository map.
- [`docs/AUTOMATION_INDEX_V0_1.md`](docs/AUTOMATION_INDEX_V0_1.md) — automation index.
- [`docs/STRATEGY_INDEX_V0_1.md`](docs/STRATEGY_INDEX_V0_1.md) — Paper baseline and research layers.
- [`docs/TRADINGAGENTS_RESEARCH_CHALLENGER_V0_1.md`](docs/TRADINGAGENTS_RESEARCH_CHALLENGER_V0_1.md) — challenger contract.
- Public dashboard: https://qookey109-pixel.github.io/crypto-autopilot/

## Preserved pre-convergence snapshot

The pre-PR-#322 long-form root documents remain exactly recoverable from historical parent main `f5cf74292fca262ba72c4e0b36f8d757dfb82531`:

- README blob: `0ce5c87ec4da228a6eb3d9a66ef2e8364661df58`
- PROJECT_STATUS blob: `0815abd975c5c708fbb9578dff400733e1ff6275`

Older statements that Core100 is `8/10` or Training is `SKIPPED` are historical evidence and must not be used to classify current operations.
