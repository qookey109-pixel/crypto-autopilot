# Project Status

Updated: 2026-09-16

Repository `main` is the formal current authority. This file is the current project-stage, governance-compatibility, and retired-workflow index. Exact versioned configs, receipts, immutable run evidence, and merged code remain the detailed authority for each scope.

## Reviewed repository authority

- Repository: `qookey109-pixel/crypto-autopilot`
- Reviewed `main`: `f5cf74292fca262ba72c4e0b36f8d757dfb82531`
- Latest merged change: PR #321, exact reviewed head `880e3ed9203719cc992362918e3858a6dc63f5ec`
- Current mode: **PAPER-ONLY**
- FREE-ONLY cloud/runtime budget: **0 USD/month**

For the concise current-operations view, read `CURRENT_STATUS.md` first. Machine-readable companion: `research/status/current-operations-v0-2.json`.

## Current lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

### Core100 History

- Detailed Core100 History acquisition is complete: `10/10` governed shards.
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
- run window: `2026-09-15T01:40:40Z` through `2026-09-15T04:38:22Z`

Training/pipeline completion is separate from model-quality acceptance.

### Model quality and threshold replay

Current model-quality result: **REJECT**.

Initial diagnosis:

- fold-1 is the only identified fold that does not beat naive log-loss.
- configured probability threshold `0.55` emitted zero signals in all four folds.
- automatic promotion remains disabled.

Exact read-only replay run: `34936331199` — `Core100 Threshold Sweep Replay V0.1`

- workflow conclusion: `success`
- execution head: `fbebb5cbe424e4a6d6c33cb6e09a12da4849ee07`
- artifact: `10387278663`
- digest: `sha256:f983f5364024a911be3f930fce641bd750922a8d95e710951b88d5738f5cfa29`
- exact dataset fingerprint preserved
- thresholds evaluated: `0.50, 0.51, 0.52, 0.53, 0.54, 0.55`
- `0.50`: fold-1 negative, fold-2 positive, fold-3/4 zero signal
- `0.51`: fold-1/2 negative, fold-3/4 zero signal
- `0.52-0.55`: zero signals in all folds
- `supported_thresholds=[]`
- `threshold_change_supported=false`
- configured threshold remains unchanged

The replay was diagnostic-only: no provider requests, R2 writes, holdout access, training publication, automatic promotion, formal trade plan, real-money order, or live-trading authority was granted.

## Pionex validation state

Pionex is the final calibration / execution-environment provenance target; Binance USD-M remains the large-scale learning database. The providers remain provenance-separated.

PR #321 is merged and adds a narrow provider historical-boundary rule for bounds-only invalid OHLC candles. It does not repair, fabricate, interpolate, or splice candles.

Current workflow: `.github/workflows/pionex-validation-materialization-v0-1.yml`

- dispatch: manual only
- public Pionex futures K-lines: authorized for this validation scope
- R2 validation-dataset writes: authorized for this validation scope
- previous run `34991627998`: fail-closed before PR #321 on three invalid `AAVE_USDT_PERP / 4H` candles
- current-main materialization: **PENDING MANUAL DISPATCH**
- private API/account data: unauthorized
- replacement holdout access: unauthorized
- training: unauthorized
- source switch: unauthorized
- promotion: unauthorized
- formal trade plan / real-money / live trading: unauthorized

Do not claim current-main Pionex validation completion until a new run from `main=f5cf7429...` is verified.

## Technical-debt cleanup

The current highest-priority technical debt is control-plane/documentation drift, not a rewrite of the trading/data core.

Tracking: `docs/TECH_DEBT_REGISTER_2026_09_16.md`

Priority sequence:

1. single current-truth entrypoint + machine-readable companion;
2. README / PROJECT_STATUS / SECURITY / Dashboard projection sync;
3. current-main open-PR triage;
4. active-workflow registry instead of hard-coded scheduler counts;
5. non-blocking quality/security/dependency visibility;
6. only then consider responsibility-splitting large modules such as `training/quality.py`.

## Open work that matters now

- PR #302 — Core100 post-training REJECT diagnosis. Its replay is complete; the PR remains Draft and requires current-main review before any merge decision.
- PR #305 — older-base current-state convergence proposal. Useful design has been reused by fresh current-main cleanup work; do not merge it unchanged.
- PR #306 — Toolkit REST / Cloudflare edge V0.2 research interface; base is older than current main and public deployment remains unauthorized.
- PR #307 — AI Resource Hub statistical-validation integration; base is older than current main and requires current-main review.
- PR #315 — Binance/Pionex data-role documentation. Parts of its architecture are already represented on current main; compare before preserving or superseding.
- PR #322 — current-main technical-debt/current-status convergence branch. Draft; merge is not self-authorized.
- PRs #166/#167/#168/#199/#249 — preserved legacy salvage drafts, not ready-to-merge work.

Historical CI success on an old branch is not sufficient merge evidence after main has advanced.

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

The research-calendar/dashboard and retired-workflow validators intentionally fail closed if these frozen stage markers disappear. They are retained as compatibility assertions; they do not grant new authority or override the current lifecycle above.

- **V0.8 HISTORICAL** — frozen prepared cutover evidence only; successor execution remained unauthorized under V0.8.
- **V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE** — historical effective authority.
- **V0.2 SELF-HOSTED SCHEDULE RETIRED** — self-hosted metadata scheduling remains retired.
- **V0.10 GITHUB-HOSTED SCHEDULE RETIRED** — V0.10 GitHub-hosted schedule remains retired after the reviewed successor transition.
- **V0.12 SUCCESSOR METADATA WINDOW** — successor metadata-only capture lineage; its bounded window is historical and no holdout-candle authority is implied.
- **REPLACEMENT HOLDOUT FROZEN_UNOPENED** — replacement holdout remains unopened.
- **HISTORICAL UNIVERSE MEMBERSHIP NOT_READY** — full-universe historical membership remains not ready.
- **TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED** — retired long-horizon pilot remains unable to materialize W1 trade-kline data.

## Current navigation

1. `CURRENT_STATUS.md`
2. `PROJECT_STATUS.md`
3. `README.md`
4. `AGENTS.md`
5. current versioned config/receipt/run evidence
6. `docs/TECH_DEBT_REGISTER_2026_09_16.md`

Machine-readable current operations state: `research/status/current-operations-v0-2.json`.

## Preserved pre-convergence snapshot

The previous long-form root documents remain exactly recoverable from reviewed main `f5cf74292fca262ba72c4e0b36f8d757dfb82531`:

- README blob: `0ce5c87ec4da228a6eb3d9a66ef2e8364661df58`
- PROJECT_STATUS blob: `0815abd975c5c708fbb9578dff400733e1ff6275`

Their old present-tense `8/10 / Training SKIPPED` statements are historical evidence and must not be treated as current operations.
