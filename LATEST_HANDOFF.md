# Qookey Crypto Autopilot — Current Handoff

Status date: 2026-09-15

Repository `main` is authority. Re-read current `main` before new work; do not use this handoff to override newer merged code, versioned configs/receipts, or immutable run evidence.

## Current authority snapshot

- Repository: `qookey109-pixel/crypto-autopilot`
- Reviewed main: `7c5604efcd55d3d7f477e5417fe26bfe0b32b9ce`
- Mode: `PAPER-ONLY`
- FREE-ONLY project budget: `0 USD/month`
- Replacement holdout: `2026-08-28..2026-09-03` = `FROZEN_UNOPENED`
- `source_switch_authorized=false`

## Current Core100 lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold/Reproducibility Diagnostics ACTIVE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

History is already complete. Do not reacquire the 10 History shards just because the model-quality gate rejected.

### Completed training

Run `34918219864`:

- workflow `success`
- training report `PASS`
- 100 symbols
- 14,274 dataset partition objects
- 18,235,427 rows
- 249,228 examples
- fingerprint `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`
- all folds ready
- quality gate `REJECT`
- automatic promotion closed

Initial diagnosis:

- fold-1 only identified log-loss failure
- model log-loss `0.6868440595395335`
- naive log-loss `0.6866175782639343`
- delta `+0.00022648127559921072`
- configured threshold `0.55` emits zero signals in all four folds

### Active replay

Run `34936331199` — `Core100 Threshold Sweep Replay V0.1`

Last verified: `in_progress` on exact execution head `fbebb5cbe424e4a6d6c33cb6e09a12da4849ee07`.

Do not cancel/rerun merely because it runs for hours. The source training run took about 2h58m and replay timeout is 330 minutes.

Candidate thresholds: `0.50..0.55` in `0.01` increments.

This is diagnostic only: no provider requests, R2 writes, holdout access, new training publication, automatic promotion, trade plan, real-money order, live trading, or source switch.

## Next execution logic

When continuing:

1. Re-read latest `main`.
2. Re-check run `34936331199`.
3. If still in progress, leave it untouched and continue only non-conflicting cleanup/validation work.
4. If completed successfully, inspect the secret-free replay artifact and verify exact dataset fingerprint, partition count, rows, example count, fold count, and quality-gate reproduction.
5. If reproducibility fails, stop model/threshold changes and diagnose lineage/dependency/seed/data-feature drift first.
6. If reproducibility passes, analyze prediction distributions and threshold -> signals -> gross return -> costs -> net return by fold.
7. Diagnose fold-1 by regime/cohort/prevalence/calibration/feature drift/underfit.
8. Only then version the next research change and consider governed retraining.

Do not open holdout, promote a model, create formal trade plans, or enable real-money/live trading without separate explicit versioned authority.

## Current PRs relevant to this stage

- PR #302 — Core100 post-training REJECT diagnosis. Active diagnostic line; do not merge before replay evidence is integrated and current main compatibility is rechecked.
- PR #305 — current-state convergence and documentation guardrail.
- PR #301 — Toolkit REST API / Cloudflare edge. Re-evaluate against already merged Toolkit V0.2; do not deploy or merge blindly.
- PR #290 — closed as superseded because it still described Core100 as `8/10`.

## Current navigation

Read:

1. `CURRENT_STATUS.md`
2. `PROJECT_STATUS.md`
3. `AGENTS.md`
4. exact stage config / receipt / immutable run evidence
5. this handoff

Machine-readable current status: `research/status/current-operations-v0-1.json`.
