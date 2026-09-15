# Project Status

Updated: 2026-09-15

Repository `main` is the formal current authority. This file is the current project-stage index; exact versioned configs, receipts, immutable run evidence, and merged code remain the detailed authority for each scope.

## Reviewed repository authority

- Repository: `qookey109-pixel/crypto-autopilot`
- Reviewed `main`: `7c5604efcd55d3d7f477e5417fe26bfe0b32b9ce`
- Current mode: **PAPER-ONLY**
- FREE-ONLY cloud/runtime budget: **0 USD/month**

## Current lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold/Reproducibility Diagnostics ACTIVE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

### Core100 History

- Detailed Core100 History acquisition is complete.
- Historical reacquisition is not required solely because the trained model was rejected by quality gates.
- Do not restart completed History shards unless new evidence demonstrates actual dataset-integrity or lineage failure.

### Core100 training

Source run: `34918219864`

- workflow conclusion: `success`
- training report status: `PASS`
- symbol count: `100`
- dataset partition objects: `14,274`
- dataset rows: `18,235,427`
- example count: `249,228`
- dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`
- all folds ready: `true`

Training/pipeline completion is separate from model-quality acceptance.

### Model quality gate

Current result: **REJECT**

- `all_folds_beat_naive_log_loss=false`
- `all_base_cost_scenarios_positive_average_return=false`
- `automatic_promotion=false`

Initial diagnosis:

- fold-1 is the only currently identified fold that does not beat naive log-loss.
- fold-1 model log-loss: `0.6868440595395335`
- fold-1 naive log-loss: `0.6866175782639343`
- delta versus naive: `+0.00022648127559921072`
- configured probability threshold: `0.55`
- all four walk-forward folds emit zero signals at `0.55`
- therefore the observed base-cost failure at the configured threshold is a zero-signal gating outcome, not observed negative post-cost return evidence.

Do not weaken the quality gate merely because the fold-1 delta is small.

## Active diagnostic stage

GitHub Actions run: `34936331199` — `Core100 Threshold Sweep Replay V0.1`

Last verified state on 2026-09-15: `in_progress`.

- execution head: `fbebb5cbe424e4a6d6c33cb6e09a12da4849ee07`
- branch: `codex/core100-reject-diagnosis-20260915`
- candidate thresholds: `0.50, 0.51, 0.52, 0.53, 0.54, 0.55`
- R2 reads: bounded one-shot diagnostic only
- R2 writes: unauthorized
- provider requests: unauthorized
- holdout access: unauthorized
- training publication: unauthorized
- automatic promotion: unauthorized
- formal trade plan / real-money / live trading: unauthorized

The original Core100 training run took about 2h58m; the replay workflow has a 330-minute timeout. Do not classify the replay as stuck merely because the exact-data reconstruction and retraining step runs for hours within that bound.

### Decision tree after replay

1. If exact replay does not reproduce the governed training result, stop threshold/model changes and diagnose dataset, feature, dependency, seed, and lineage reproducibility first.
2. If exact replay reproduces the governed result, freeze replay evidence and analyze probability distributions plus threshold -> signal count -> gross return -> cost -> net return curves.
3. Diagnose fold-1 by regime, symbol cohort, prevalence, calibration, feature drift, and underfit.
4. Only then create a new version deciding whether the next research change belongs in calibration, features, labels, model configuration, or strategy gating.
5. Holdout, promotion, formal trade plans, real-money orders, and live trading remain closed unless separately authorized.

## Other current components

### Qookey Crypto Toolkit V0.2

Merged on current `main`. Research-only cloud commands cover capabilities, validation, indicators, strategy, risk, backtest, stress, compare, and report. Provider/R2 access, holdout, source switching, automatic strategy mutation, model promotion, trade plans, real-money orders, and live trading remain disabled.

### TradingAgents Research Challenger V0.1

Merged as `PREPARED_RESEARCH_ONLY`. It is offline and non-authoritative. No upstream LLM/provider calls, R2 operation, holdout access, strategy/risk mutation, trade plan, or order is authorized.

## Open work that matters now

- PR #302: Core100 post-training REJECT diagnosis. Keep unmerged while replay evidence is still being produced and interpreted.
- PR #305: current-state convergence / documentation guardrail work.
- PR #301: Toolkit REST API + Cloudflare edge remains separate and must be re-evaluated against merged Toolkit V0.2 before any future merge or deployment decision.
- PR #290 was closed as superseded because it still described the obsolete Core100 `8/10` state.

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

The research-calendar/dashboard and retired-workflow validators intentionally fail closed if these frozen stage markers disappear. They are retained here as compatibility assertions; they do not grant new authority or override the current lifecycle above.

- **V0.8 HISTORICAL** — frozen prepared cutover evidence only; successor execution remained unauthorized under V0.8.
- **V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE** — historical effective authority.
- **V0.2 SELF-HOSTED SCHEDULE RETIRED** — self-hosted metadata scheduling remains retired.
- **V0.10 GITHUB-HOSTED SCHEDULE RETIRED** — V0.10 GitHub-hosted schedule remains retired after the reviewed successor transition.
- **V0.12 SUCCESSOR METADATA WINDOW** — successor metadata-only capture lineage; no holdout-candle authority is implied.
- **REPLACEMENT HOLDOUT FROZEN_UNOPENED** — replacement holdout remains unopened.
- **HISTORICAL UNIVERSE MEMBERSHIP NOT_READY** — full-universe historical membership remains not ready.
- **TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED** — retired long-horizon pilot remains unable to materialize W1 trade-kline data.

## Current navigation

1. `CURRENT_STATUS.md`
2. `PROJECT_STATUS.md`
3. `AGENTS.md`
4. current versioned config/receipt/run evidence
5. `LATEST_HANDOFF.md`

Machine-readable current operations state: `research/status/current-operations-v0-1.json`.

Historical long-form status previously at the root is preserved at `docs/archive/PROJECT_STATUS_2026_09_13.md` and remains dated evidence only.
