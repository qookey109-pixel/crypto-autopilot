# Qookey Crypto Autopilot

Cloud-first, exchange-agnostic crypto trading research and automation platform.

> **Current mode: PAPER-ONLY.** No formal trade plan, real-money order, automatic model promotion, source switch, or live-trading path is authorized.

## Start here

For current work, read in this order:

1. [`CURRENT_STATUS.md`](CURRENT_STATUS.md) — concise current operations state.
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — project-stage, governance, compatibility and retired-workflow index.
3. [`AGENTS.md`](AGENTS.md) — execution and safety rules for coding agents.
4. The exact versioned config, receipt, and immutable run evidence for the stage being changed.

Repository `main` is the formal current authority. Dated documents, archived snapshots and dashboards are evidence/projections, not permission to regress current lifecycle state.

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

PR #321 is merged on reviewed `main=f5cf74292fca262ba72c4e0b36f8d757dfb82531` and narrowly treats bounds-only invalid OHLC candles as a provider historical boundary without correcting or fabricating candles.

The current validation workflow is `.github/workflows/pionex-validation-materialization-v0-1.yml` and remains manual-only. The previous authorized run `34991627998` failed closed before the PR #321 fix. A new run from current main is still required before current-main Pionex validation can be called complete.

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

The current highest-priority technical debt is control-plane/documentation drift rather than a rewrite of the trading/data core.

- Human current entrypoint: [`CURRENT_STATUS.md`](CURRENT_STATUS.md)
- Machine-readable current state: [`research/status/current-operations-v0-2.json`](research/status/current-operations-v0-2.json)
- Cleanup register: [`docs/TECH_DEBT_REGISTER_2026_09_16.md`](docs/TECH_DEBT_REGISTER_2026_09_16.md)

Cleanup order is current-truth convergence -> README/PROJECT_STATUS/SECURITY/Dashboard projection sync -> PR/workflow registry cleanup -> non-blocking quality/security/dependency visibility -> only then large-module refactoring.

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

The previous long-form root documents are historical evidence and remain exactly recoverable from reviewed main `f5cf74292fca262ba72c4e0b36f8d757dfb82531`:

- README blob: `0ce5c87ec4da228a6eb3d9a66ef2e8364661df58`
- PROJECT_STATUS blob: `0815abd975c5c708fbb9578dff400733e1ff6275`

Older statements that Core100 is `8/10` or Training is `SKIPPED` must not be used to classify current operations.
