# Qookey Crypto Autopilot

Cloud-first, exchange-agnostic crypto trading research and automation platform.

> **Current mode: PAPER-ONLY.** No formal trade plan, real-money order, automatic model promotion, source switch, or live-trading path is authorized.

## Start here

For current work, read in this order:

1. [`CURRENT_STATUS.md`](CURRENT_STATUS.md) — concise current operations state.
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — current project-stage and governance index.
3. [`AGENTS.md`](AGENTS.md) — execution and safety rules for coding agents.
4. The exact versioned config, receipt, and immutable run evidence for the stage being changed.

Repository `main` is the formal current authority. Dated documents and archived snapshots are historical evidence, not permission to regress current lifecycle state.

## Current Core100 state — 2026-09-15

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold/Reproducibility Diagnostics ACTIVE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

- Detailed Core100 History acquisition is complete. Do **not** restart the 10-shard History program solely because model quality rejected.
- Source training run: `34918219864`.
- Training pipeline/report: `success / PASS`.
- Dataset: 100 symbols, 14,274 partition objects, 18,235,427 rows, 249,228 examples.
- Dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
- Model quality gate: **REJECT**.
- `all_folds_beat_naive_log_loss=false`.
- `all_base_cost_scenarios_positive_average_return=false`.
- `automatic_promotion=false`.
- Initial diagnosis: fold-1 is the only identified log-loss failure; configured threshold `0.55` emitted zero signals in all four folds.
- Active diagnostic run: `34936331199` (`Core100 Threshold Sweep Replay V0.1`), read-only diagnostic authority only.

The replay tests candidate thresholds `0.50` through `0.55` without changing the quality gate, publishing a new model, opening holdout data, or authorizing trading.

## Current research components

### Qookey Crypto Toolkit V0.2

Merged on current `main`. Cloud-first, research-only deterministic commands cover capabilities, validation, indicators, strategy, risk, backtest, stress, compare, and report. Provider/R2 access, holdout access, automatic strategy mutation, model promotion, formal trade plans, real-money orders, and live trading remain disabled.

### TradingAgents Research Challenger V0.1

Merged as `PREPARED_RESEARCH_ONLY`. It is an offline, non-authoritative research-context adapter. It does not authorize upstream LLM/provider calls, R2 operations, holdout access, strategy/risk mutation, trade plans, or orders.

## Safety boundaries

- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- `source_switch_authorized=false` remains binding.
- Pionex-native and Binance USD-M evidence must remain provenance-separated.
- Project cloud/runtime budget remains **0 USD/month** for the FREE-ONLY path.
- Render must never receive R2 credentials.
- Secrets must never be committed, logged, artifacted, or pasted into chat.
- Frozen configs/receipts/evidence are immutable; create a new version instead of rewriting history.

## Historical authority lineage compatibility

The current project still preserves the frozen lineage names required by fail-closed authority tests:

- **V0.8** remains historical prepared/cutover evidence only.
- **V0.10** remains the historical effective final atomic metadata-capture cutover lineage; its GitHub-hosted schedule is retired.
- **V0.12** remains the successor metadata-window lineage and the unique scheduled metadata-capture successor for its frozen window.
- **Equivalence V0.1** remains a definitive FAIL and must not be regraded by changing scope or thresholds.
- Replacement holdout remains **FROZEN_UNOPENED**.

These historical labels preserve governance lineage; they do not reopen provider access, holdout access, model promotion, source switching, or trading authority.

## Useful entrypoints

- [`docs/PROJECT_MAP_V0_1.md`](docs/PROJECT_MAP_V0_1.md) — repository map.
- [`docs/AUTOMATION_INDEX_V0_1.md`](docs/AUTOMATION_INDEX_V0_1.md) — active/scheduled automation index.
- [`docs/STRATEGY_INDEX_V0_1.md`](docs/STRATEGY_INDEX_V0_1.md) — Paper baseline and research layers.
- [`docs/TRADINGAGENTS_RESEARCH_CHALLENGER_V0_1.md`](docs/TRADINGAGENTS_RESEARCH_CHALLENGER_V0_1.md) — challenger contract.
- [`LATEST_HANDOFF.md`](LATEST_HANDOFF.md) — current continuation handoff.
- Public dashboard: https://qookey109-pixel.github.io/crypto-autopilot/

## Historical snapshots

The previous long-form root summaries are preserved as dated historical evidence:

- [`docs/archive/README_2026_09_13.md`](docs/archive/README_2026_09_13.md)
- [`docs/archive/PROJECT_STATUS_2026_09_13.md`](docs/archive/PROJECT_STATUS_2026_09_13.md)

They must not be used to classify current Core100 as `8/10` or current training as `SKIPPED`.
