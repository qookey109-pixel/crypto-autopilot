# Current Operations Status

Updated: 2026-09-15

This file is the concise current-operations entrypoint. Repository `main`, versioned configs/receipts, and immutable run evidence remain the formal authority. Older dated sections in `PROJECT_STATUS.md` remain historical evidence and must not be treated as the newest operational state when this file records a later verified state.

## Reviewed repository authority

- Repository: `qookey109-pixel/crypto-autopilot`
- Reviewed `main`: `7c5604efcd55d3d7f477e5417fe26bfe0b32b9ce`
- `main` includes PR #303, Qookey Crypto Toolkit V0.2 cloud-first analysis tools.
- Latest reviewed push CI and V0.10 Critical Path Freeze Guard on this `main` revision passed.

## Current Core100 lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold/Reproducibility Diagnostics ACTIVE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

### History

- Core100 detailed history acquisition is complete.
- Historical reacquisition is **not required** solely because the model-quality gate rejected the trained model.
- Do not restart the 10-shard History program unless new evidence identifies an actual dataset-integrity failure.

### Training

Source training run: `34918219864`

- workflow conclusion: `success`
- training report: `PASS`
- symbols: `100`
- dataset partition objects: `14,274`
- dataset rows: `18,235,427`
- training examples: `249,228`
- dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`
- all folds ready: `true`
- source run wall-clock duration was approximately `2h 58m` (`01:40:40Z` to `04:38:22Z`)

Operational pipeline success does **not** mean the model passed research quality gates.

### Model quality gate

Current outcome: **REJECT**

- `all_folds_beat_naive_log_loss = false`
- `all_base_cost_scenarios_positive_average_return = false`
- `automatic_promotion = false`

Initial diagnosis found:

- fold-1 is the only fold currently identified as failing the naive log-loss comparison.
- fold-1 model log-loss: `0.6868440595395335`
- fold-1 naive log-loss: `0.6866175782639343`
- delta versus naive: `+0.00022648127559921072`
- at the configured `0.55` probability threshold, all four walk-forward folds emitted zero signals.
- the base-cost failure is therefore currently a zero-signal gating problem at `0.55`, not evidence of observed negative post-cost returns.

Do not loosen the quality gate merely because the fold-1 delta is small.

## Active diagnostic work

Observed GitHub Actions run: `34936331199` — `Core100 Threshold Sweep Replay V0.1`

At the last 2026-09-15 verification, this run was still `in_progress` on branch `codex/core100-reject-diagnosis-20260915`.

Important lineage distinction:

- replay run head: `fbebb5cbe424e4a6d6c33cb6e09a12da4849ee07`
- current diagnosis branch head: `3f2416d8b63b27e8dc29d7d94469792c87dd9e03`
- the current branch head is the immediate child of the replay head and only retires the one-shot replay trigger after launch.

Therefore, evaluate run `34936331199` against its own exact run head `fbebb5c...`, not against the later branch head.

The currently running step is:

`Replay exact governed dataset without publishing training`

Runtime guidance:

- replay workflow timeout: `330 minutes`
- the source training run needed about `2h 58m`
- because replay rebuilds examples from the governed R2 dataset and reruns the same training path with threshold diagnostics, a long-running replay is expected; do not cancel or rerun it merely because it remains active for tens of minutes or a few hours within its timeout.

The one-shot diagnostic authority is bounded to candidate thresholds:

`0.50, 0.51, 0.52, 0.53, 0.54, 0.55`

It authorizes read-only diagnostic replay only. It does not authorize R2 writes, provider requests, holdout access, model publication, automatic promotion, formal trade plans, real-money orders, live trading, or source switching.

### Decision tree after replay

1. If exact replay does **not** reproduce the governed training result, stop threshold/model changes and diagnose lineage, dataset, feature, dependency, seed, or reproducibility differences first.
2. If exact replay **does** reproduce the governed training result, freeze replay evidence and analyze probability distributions plus threshold -> signal count -> gross return -> cost -> net return curves.
3. Diagnose fold-1 by regime, cohort, prevalence, calibration, feature drift, and underfit before selecting a retraining change.
4. Only after that evidence should a new version decide whether to change calibration, features, labels, model configuration, or strategy gating.
5. Holdout, promotion, formal trade plans, real-money orders, and live trading remain closed unless separately authorized.

## Other current research components

### Qookey Crypto Toolkit V0.2

Merged on current `main`. It provides cloud-first, research-only commands for capabilities, validation, indicators, strategy, risk, backtest, stress, compare, and report. Its authority boundary keeps provider access, R2 access, holdout access, source switching, automatic strategy mutation, automatic model promotion, formal trade plans, real-money orders, and live trading disabled.

### TradingAgents Research Challenger V0.1

Merged as `PREPARED_RESEARCH_ONLY`. It is an offline, non-authoritative research-context adapter. No upstream LLM/provider call, R2 operation, holdout access, strategy/risk mutation, trade plan, or order is authorized.

## Open PR navigation

Open pull requests are operationally classified in `docs/OPEN_PR_TRIAGE_2026_09_15.md`.

- `ACTIVE`: #302, #305, #306.
- Pionex simulation/history stack #255/#257/#258/#260/#261/#262 is `DEFERRED_STACK`; do not treat it as the current Core100 next action.
- #256 is a `HISTORICAL_EVIDENCE_CANDIDATE` pending proof that equivalent immutable evidence is already preserved on current `main`.
- #166/#167/#168/#199/#220/#249 are `REVIEW_REQUIRED_LEGACY`; preserve until file-level comparison proves supersession or their unique content is migrated.
- PR #290 and PR #301 have already been closed as superseded.

This classification is navigation only. It does not authorize merge or execution.

## Safety and governance still binding

- Current mode: **PAPER-ONLY**.
- `source_switch_authorized=false`.
- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- Pionex-native and Binance USD-M evidence must remain provenance-separated.
- Project cloud/runtime budget remains `0 USD/month` for the FREE-ONLY path.
- Render must never receive R2 credentials.
- Secrets must never be committed, logged, artifacted, or pasted into chat.
- Frozen historical evidence must not be rewritten to make a later stage appear successful.

## Documentation drift rule

`PROJECT_STATUS.md` and `README.md` contain dated historical summaries. The September 13 sections that say Core100 is `8/10` and training is `SKIPPED` are preserved historical observations and are now superseded for current operations by this September 15 status.

Do not use those older statements to restart History or to classify current training as incomplete.

Machine-readable companion: `research/status/current-operations-v0-1.json`.
