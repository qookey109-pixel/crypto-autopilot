# Project Status

Updated: 2026-09-16

Repository `main` is the formal current authority and must be resolved live at read time. This file is the project-stage, governance-compatibility, and retired-workflow index. Exact versioned configs, receipts, immutable run evidence, and merged code remain the detailed authority for each scope.

## Current authority semantics

- Repository: `qookey109-pixel/crypto-autopilot`.
- Current Operations companion: `research/status/current-operations-v0-3.json`.
- Current Operations V0.3 stores an **evidence-basis parent SHA**, not a self-referential latest-main claim.
- Evidence-basis parent for V0.3: `a8f64ca1b2ecfbec6e6d9769fa3726dc007aa266`, the main commit after PR #322 merged and passed post-merge CI/Pages/Freeze Guard.
- Current mode: **PAPER-ONLY**.
- FREE-ONLY cloud/runtime budget: **0 USD/month**.

For present-tense operations read `CURRENT_STATUS.md` first, then resolve the Repository's live `main`. Dated prose and dashboard fixtures are evidence/projections, not substitutes for live Repository authority.

## Current lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

### Core100 History and training

- Detailed Core100 History acquisition is complete: `10/10` governed shards.
- Historical reacquisition is not required solely because the trained model was rejected by quality gates.
- Training run `34918219864`: workflow `success`, report `PASS`.
- 100 symbols; 14,274 dataset partition objects; 18,235,427 rows; 249,228 examples.
- Dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
- All folds ready: `true`.

Training/pipeline completion is separate from model-quality acceptance.

### Model quality and threshold replay

Current model-quality result: **REJECT**.

Exact read-only replay run `34936331199` completed successfully on the same dataset fingerprint:

- thresholds evaluated: `0.50, 0.51, 0.52, 0.53, 0.54, 0.55`;
- `supported_thresholds=[]`;
- `threshold_change_supported=false`;
- configured threshold remains unchanged;
- automatic model promotion remains disabled.

The replay is diagnostic-only and grants no provider request, R2 write, holdout, promotion, trade-plan, order, or live-trading authority.

## Pionex validation state

Pionex is the final calibration / execution-environment provenance target; Binance USD-M remains the large-scale learning database. The providers remain provenance-separated.

PR #321 merged the narrow bounds-only invalid-OHLC historical-boundary rule without repairing, fabricating, interpolating, or splicing candles.

Current workflow: `.github/workflows/pionex-validation-materialization-v0-1.yml`

- dispatch: manual only;
- public Pionex futures K-lines: authorized for this validation scope;
- R2 validation-dataset writes: authorized for this validation scope;
- previous run `34991627998`: fail-closed before PR #321;
- Repository materialization state: **PENDING MANUAL DISPATCH**;
- private API/account data: unauthorized;
- replacement holdout access: unauthorized;
- training: unauthorized;
- source switch: unauthorized;
- promotion: unauthorized;
- formal trade plan / real-money / live trading: unauthorized.

The next materialization must be dispatched from the Repository's **live `main` at dispatch time**. Do not pin execution to the status file's evidence-basis SHA.

## Technical-debt cleanup

PR #322 merged the first control-plane convergence batch:

- current-operations entrypoint plus machine-readable companion;
- README / PROJECT_STATUS / SECURITY / AGENTS convergence;
- current-main PR triage;
- Research Automation Health count derived from exact Repository schedule inventory rather than a magic `7`;
- first fail-closed Dashboard current-operations overlay implementation.

The active follow-up removes two remaining projection defects:

1. Current Status must not self-claim a future/latest merge SHA; V0.3 uses evidence-basis semantics instead.
2. Public Dashboard/Homepage must apply present-tense Current Operations after historical authority/readiness projections, so dated September 13 `8/10 / Training skipped / PR #292` text cannot return during deployment.

After projection convergence, remaining P2 debt is non-blocking quality/type/complexity/dependency/security visibility. Large-module refactoring remains deferred until the control plane is stable.

Tracking: `docs/TECH_DEBT_REGISTER_2026_09_16.md`.

## Open work that matters now

- PR #322 is **MERGED**; its merge commit/evidence basis is `a8f64ca1b2ecfbec6e6d9769fa3726dc007aa266`.
- PR #302 — preserve Core100 post-training REJECT diagnostic evidence; old branch code still requires current-main review before any merge decision.
- PR #305 — older-base convergence proposal; superseded in purpose by merged #322 and current V0.3 follow-up, but unique content must be checked before closure.
- PR #306 — Toolkit REST / Cloudflare edge V0.2; rebuild from current main if revived; public deployment remains unauthorized.
- PR #307 — AI Resource Hub statistical-validation integration; rebuild from current main if revived.
- PR #315 — Binance/Pionex data-role documentation; compare unique content against current merged architecture before preserving or closing.
- PRs #166/#167/#168/#199/#249 — preserved legacy salvage drafts, not ready-to-merge work.

Historical CI success on an old branch is not sufficient merge evidence after main advances.

## Binding safety and governance

- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- `source_switch_authorized=false`.
- Pionex-native and Binance USD-M evidence remain provider-separated and must never be relabeled.
- **Equivalence V0.1** remains a definitive FAIL; thresholds and scope are frozen and must not be regraded.
- No martingale, loss-doubling, or unlimited averaging down.
- Render Free / Frankfurt remains the proven public-metadata transport leg where applicable.
- Render must never receive R2 credentials.
- R2 credentials stay inside authorized GitHub Actions/local secret boundaries only.
- Frozen receipts/configs/evidence must not be rewritten to make later stages appear successful.
- Dashboards are derived evidence projections, not authority.
- Backtests and research metrics are evidence, not proof of future profitability.

## Reproducibility and CI hardening lineage

These markers preserve the reviewed engineering-hardening lineage required by repository authority tests; they do not add runtime authority.

- Dependency reproducibility uses `requirements/ci-constraints.txt` and validates the supported **Python 3.12 and Python 3.13** matrix, including jobs `test (3.12)` and `test (3.13)`.
- Production-critical GitHub Actions are pinned to **immutable 40-character commit SHAs**; the Python 3.13 runtime path remains explicitly validated.
- PR #136 and PR #137 established the constrained dependency/reproducibility hardening baseline; PR #140 continued the reviewed workflow hardening lineage.
- `D1_DATABASE_ID` is intentionally not a secret placeholder in `.env.example`; PR #141 records the related environment/authority cleanup lineage.
- Ruff is constrained as `ruff==0.16.0` and CI enforces core correctness classes `E4`, `E7`, and `E9`.
- PR #142 and PR #143 preserve the reviewed CI `pull_request` validation and supported Python matrix lineage.
- Issue #139 remains historical engineering context for this reproducibility-hardening sequence.

## Retired historical workflow inventory

Exactly **17 historical workflows** remain retired evidence/validation paths and must not be silently reactivated:

- `historical-backfill-pilot.yml`
- `diagnose-v0-2-self-hosted-mac-binance-transport.yml`
- `binance-2025-r2-pilot.yml`
- `binance-vision-live-proof.yml`
- `binance-vision-r2-proof.yml`
- `binance-funding-r2-v0-2-preflight.yml`
- `binance-funding-r2-v0-2-materialize.yml`
- `m1b-m1a-dataset-upload.yml`
- `m1b-r2-roundtrip.yml`
- `binance-2025-coverage-scan.yml`
- `binance-funding-source-proof.yml`
- `binance-funding-coverage.yml`
- `binance-max-coverage-discovery.yml`
- `m1a-acquisition.yml`
- `pionex-binance-equivalence-proof.yml`
- `pionex-binance-equivalence-v0-1-forensics.yml`
- `historical-universe-long-horizon-review.yml`

## Frozen historical lineage and dashboard compatibility markers

The dashboard and retired-workflow validators intentionally preserve these historical stage names. They do not override current operations or grant new authority.

- **V0.8 HISTORICAL** — frozen prepared cutover evidence only.
- **V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE** — historical effective authority.
- **V0.2 SELF-HOSTED SCHEDULE RETIRED** — self-hosted metadata scheduling remains retired.
- **V0.10 GITHUB-HOSTED SCHEDULE RETIRED** — V0.10 GitHub-hosted schedule remains retired.
- **V0.12 SUCCESSOR METADATA WINDOW** — frozen successor metadata-only lineage. Its bounded window is historical; current projections must not call it an active execution path.
- **REPLACEMENT HOLDOUT FROZEN_UNOPENED** — replacement holdout remains unopened.
- **HISTORICAL UNIVERSE MEMBERSHIP NOT_READY** — full-universe historical membership remains not ready.
- **TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED** — retired long-horizon pilot remains unable to materialize W1 trade-kline data.

## Current navigation

1. `CURRENT_STATUS.md`
2. `research/status/current-operations-v0-3.json`
3. `PROJECT_STATUS.md`
4. `README.md`
5. `AGENTS.md`
6. current versioned config/receipt/run evidence
7. `docs/TECH_DEBT_REGISTER_2026_09_16.md`

## Preserved pre-convergence snapshot

The pre-PR-#322 long-form root documents remain exactly recoverable from historical parent main `f5cf74292fca262ba72c4e0b36f8d757dfb82531`:

- README blob: `0ce5c87ec4da228a6eb3d9a66ef2e8364661df58`
- PROJECT_STATUS blob: `0815abd975c5c708fbb9578dff400733e1ff6275`

Their old present-tense `8/10 / Training SKIPPED` statements are historical evidence and must not be treated as current operations.
