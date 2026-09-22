# Project Status

Updated: 2026-09-22

Repository `main` is the formal current authority and must be resolved live at read time. This file is the project-stage, governance-compatibility, and retired-workflow index. Exact versioned configs, receipts, immutable run evidence, and merged code remain the detailed authority for each scope.

## Current authority semantics

- Repository: `qookey109-pixel/crypto-autopilot`.
- Current Operations companion: `research/status/current-operations-v0-3.json`.
- Current Operations V0.3 stores an **evidence-basis parent SHA**, not a self-referential latest-main claim.
- Evidence-basis parent for this status version: `09dfb0d79b88dc56f3cb582c91d8091617437ce2`, the reviewed main commit after PR #426 merged and passed post-merge CI / Freeze Guard / CodeQL / Pages.
- Current mode: **PAPER / LIVE-PAPER ONLY**. Public live market data and simulated live-paper execution/persistence are separate from real trading authority.
- FREE-ONLY cloud/runtime budget: **0 USD/month**.

For present-tense operations read `CURRENT_STATUS.md` first, then resolve the Repository's live `main`. Dated prose and dashboard fixtures are evidence/projections, not substitutes for live Repository authority.

## Current lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> REAL TRADING CLOSED / LIVE-PAPER SEPARATELY AUTHORIZED`

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

Current workflow: `.github/workflows/pionex-validation-materialization-v0-2.yml`

Repository materialization state: **COMPLETE / PASS**.

- final successful run: `35054729471`;
- run head SHA: `5eaf57133d013fad030681182b379a02d915766e`;
- report stage: `PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_2`;
- selected markets: `197`;
- partitions: `682`;
- provider requests: `1,534`;
- artifact: `10430054351`;
- artifact digest: `sha256:5f8c3406ee5dc9a491cd800241c1cc7e2dd66bc98fa292da1c8bb05535dede55`;
- manifest key: `market-data/pionex/validation-dataset-v0.2/runs/run=github-35054729471-1/manifest.json`;
- manifest SHA-256: `192eddd1c69dd435d2ea12a0bf68e05e1cbc1a0fd512f4321f631755c61ca225`;
- R2 latest pointer written last: `true`;
- completion evidence: `research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json`.

The completed dataset preserves explicit provider-coverage states. It does **not** claim complete 197-market multiyear history, and it did not perform Core100 Pionex training.

The repair lineage remains narrow and provider-native:

- PR #321 preserved bounds-only invalid-candle historical boundaries without repair/fabrication;
- PR #332 introduced V0.2 native `1D -> logical 1W` construction;
- PR #334 preserved explicit `NO_PROVIDER_HISTORY_BEFORE_CUTOFF` zero-history coverage;
- PR #335 preserved explicit provider-latest-before-cutoff trailing coverage without interpolation or splicing;
- PR #337 recorded the successful V0.2 materialization completion evidence.

Authority after PASS remains unchanged:

- public Pionex futures K-lines: authorized only for the governed validation scope;
- R2 validation-dataset writes: authorized only for the governed validation scope;
- private API/account data: unauthorized;
- replacement holdout access: unauthorized;
- training: unauthorized;
- source switch: unauthorized;
- promotion: unauthorized;
- formal real-money trade plan / real-money orders / real live trading: unauthorized.
- public-market-data live-paper simulation is governed separately by `config/live_paper_simulation_v0_1.json` and does not change the validation-dataset authority above.

**Materialization PASS is not Model Quality PASS.** Strategy Validation, Holdout, Promotion, and Trading remain closed because the Core100 model-quality result remains **REJECT** and threshold replay supports no threshold change.

## Technical-debt cleanup

PR #322 merged the first control-plane convergence batch:

- current-operations entrypoint plus machine-readable companion;
- README / PROJECT_STATUS / SECURITY / AGENTS convergence;
- current-main PR triage;
- Research Automation Health count derived from exact Repository schedule inventory rather than a magic `7`;
- first fail-closed Dashboard current-operations overlay implementation.

The control plane must keep present-tense Current Operations later than historical authority/readiness projections, so dated September 13 `8/10 / Training skipped / PR #292` text and older V0.1 Pionex pending-dispatch text cannot return during deployment.

P2 quality/dependency/security visibility is now established through non-blocking Quality Visibility V0.2, non-blocking mypy semantic type visibility, review-only Dependabot proposals, and non-blocking CodeQL SARIF artifacts. The first mypy baseline reported 261 type errors and remains informational only; no type/security threshold is a required gate. Large-module refactoring remains deferred under TD-009.

Tracking: `docs/TECH_DEBT_REGISTER_2026_09_17.md`. Current PR navigation: `docs/OPEN_PR_TRIAGE_2026_09_22.md` / `research/status/open-pr-triage-v0-6.json`.

## Open work that matters now

- Pionex Validation Materialization V0.2 is **COMPLETE / PASS** on run `35054729471`; this closes the materialization task only, not downstream research gates.
- Core100 remains **Model Quality REJECT** and threshold replay still supports **no threshold change**; Strategy Validation, replacement holdout, Promotion and real trading remain closed.
- ZEC MACD V0.2 historical evidence is preserved on current main as **execution PASS / strategy evidence REJECT**. No V0.1/V0.2 reexecution authority was revived.
- ZEC Strategy V0.3 completed its governed one-shot historical development execution: 64 candidates × 4 folds = 256/256 cells. Selection result is **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**; no champion was frozen. Fresh confirmation, holdout, promotion and trading remain unopened.
- External Capability Registry candidates have downstream evaluation receipts and a convergence index. Candidate inventory status does not imply runtime approval.
- Operator messaging now has a provider-neutral offline path: parser -> status resolver -> local CLI for `help`, `status` and `paper_status`; no Telegram/network/secret/trading authority is implied.
- As of the 2026-09-22 triage refresh, the active open backlog is **seven pull requests**: narrow typing cleanup #441 plus six Dependabot proposals (#326–#331). Older architecture-generation and draft-salvage PRs are closed historical references and are not current merge candidates.

Historical CI success on an old branch is not sufficient merge evidence after main advances. Any newly opened PR must be evaluated against live `main`.

## Binding safety and governance

- Live Paper Simulation V0.1 permits current public Pionex market data, simulated paper fills/lifecycle/account updates, and explicit paper-state persistence only; it has no private exchange-order path.
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
7. `docs/TECH_DEBT_REGISTER_2026_09_17.md`
8. `docs/OPEN_PR_TRIAGE_2026_09_22.md`

## Preserved pre-convergence snapshot

The pre-PR-#322 long-form root documents remain exactly recoverable from historical parent main `f5cf74292fca262ba72c4e0b36f8d757dfb82531`:

- README blob: `0ce5c87ec4da228a6eb3d9a66ef2e8364661df58`
- PROJECT_STATUS blob: `0815abd975c5c708fbb9578dff400733e1ff6275`

Their old present-tense `8/10 / Training SKIPPED` statements are historical evidence and must not be treated as current operations.


## Automation V2 Batch 2 — external research and website projection

Automatic Operations V0.5 is the current schedule classification. Repository/Health retain eight cron declarations, while seven are current-effective; the eighth is the expired frozen V0.12 declaration. V0.4 preserves the prior unclassified eight-workflow state, and V0.2 remains byte-stable because the History Cadence authority binds it as frozen evidence.

This batch adds a versioned, read-only external-source change watch and a
non-authoritative automation schedule projection.

- Resource Hub Supply Chain V0.2: daily `01:13 UTC` / `09:13 Asia/Taipei`;
  unchanged source commits return `NO_CHANGE` without rebuilding candidates.
- Changed Resource Hub candidates remain `REVIEW_REQUIRED`; automatic install,
  runtime, adapter creation and pull-request creation remain closed.
- Dashboard Pages adds a daily `04:43 UTC` / `12:43 Asia/Taipei` backstop and
  business-content hash deduplication so rebuild timestamps alone do not cause
  a deployment.
- The website projects active, waiting-authority and planned schedules
  separately through `web/data/operations-schedule.json` with
  `authority=false`.
- ZEC V0.3 remains `0/256` development cells and
  `offline_development_runner_authorized=false`.
- Hourly multi-asset Paper scheduling remains waiting for a separate authority.
- Core100 History is complete 10/10 and its acquisition cron is retired; only bounded manual diagnosis/repair remains.
- Core100 Training remains scheduled with experiment-fingerprint `NO_CHANGE` deduplication active.

This batch does not open replacement holdout, source switching, automatic model
promotion, formal trade plans, real-money orders or live real trading.


## Automation V2 P1 — Core100 lifecycle cleanup (effective on reviewed merge)

This branch prepares the next protected-main lifecycle cleanup without changing
the completed research result:

- Core100 History remains **10/10 COMPLETE** and
  `history_reacquisition_required=false`.
- The old `:23 every two hours` History cron is removed on merge.
- Generic History `auto / discover / backfill` entrypoints are retired; only
  the already-bounded diagnosis and BNX repair modes remain available.
- The 2026-09-12 History cadence config, receipt and exact old workflow bytes
  remain frozen historical evidence. The old receipt is not rewritten.
- Automatic Operations V0.4 contains **8 repository cron workflows** after the
  History schedule retirement.
- Core100 weekly Training remains scheduled, but V0.3 of the runner computes an
  experiment fingerprint from the governed dataset plus model-affecting Git
  blobs. An exact match returns `NO_CHANGE`, performs no training and writes
  nothing to R2.
- The first dedupe baseline is the already-successful run `34918219864` on
  dataset fingerprint
  `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
  The model-affecting inputs were verified byte-identical between that run head
  and reviewed main before this change.

This P1 change adds no provider scope, no new R2 scope, no holdout access, no
source switch, no automatic model promotion, no formal trade plan, no
real-money orders and no live real trading.


## Automation V3 P2 — schedule and freshness convergence

- Provider Equivalence V0.12 is a frozen critical path, so its cron declaration is
  preserved byte-for-byte even though the bounded 2026-09-04 through 2026-09-12
  window has expired. Its window gate makes post-window execution ineffective;
  replay/backfill stays closed.
- Automatic Operations V0.5 classifies eight Repository cron declarations:
  seven current-effective plus one expired frozen V0.12 declaration.
- Research Automation Health V0.2 remains the exact eight-declaration monitor and
  is the single source for freshness thresholds / effective periods used by the
  seven current-effective Dashboard jobs.
- CI requires Repository cron declarations, Automatic Operations, Health monitoring,
  and the seven-job website effective subset to obey the exact 8 / 8 / 7 + 1 relation.
- The Dashboard exposes Repo declaration / Health / current-effective / Website
  counts while remaining `authority=false`.
- This convergence adds no provider, R2, holdout, source-switch, promotion,
  trade-plan, real-money-order, or live-real-trading authority.


## Automation V3 P3 — dashboard operations monitoring

- Cloud execution projection is upgraded to `qookey-cloud-run-status-v0.2`.
- The monitor derives its eight cron declarations from Automatic Operations V0.5
  and Research Automation Health V0.2 instead of a six-workflow hard-coded list.
- It preserves the current lifecycle split: seven `CURRENT_EFFECTIVE` schedules
  plus the frozen expired V0.12 cron declaration.
- Each row exposes operation ID, authority state/path, latest automatic schedule
  run ID, exact head SHA, evidence time, execution state, freshness state, and
  GitHub evidence links.
- Workflow success is never converted into a research/trading/business PASS.
  Business result stays `UNKNOWN_FROM_GITHUB_RUN_METADATA` unless a separate
  governed artifact/receipt surface is added later.
- The collector reads GitHub Actions metadata only: no workflow logs, artifacts,
  provider data, R2 objects, holdout, private APIs, or trading surfaces.
- The checked-in fixture contains no invented run IDs, SHAs, or evidence times;
  the GitHub Pages build refreshes those fields from live GitHub metadata.


## Automation V3 P5 — ZEC V0.4 regime-activation preregistration

- V0.3 remains **256/256 COMPLETE / NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**.
- V0.4 does not loosen the V0.3 selection gate and does not promote the V0.3 diagnostic leader.
- The new hypothesis tests whether a small causal 4h bull-regime activation layer can reduce the strong time-regime dependence seen in V0.3.
- Candidate matrix is reduced to **2 MACD × 3 activation regimes = 6 candidates**, across the same four annual development folds = **24 cells**.
- Account-risk sweep is removed; risk is fixed at 1% for edge discovery.
- ATR extreme guard and 2.5ATR/Bollinger stop are fixed to reduce degrees of freedom.
- Fresh confirmation remains unopened.
- This phase is **contract validation only**: no runner, workflow dispatch, provider read, R2 access, holdout access, source switch, promotion or trading authority is added.


## ZEC V0.4 one-shot development authority

PR #418 prepares a **manual one-shot** execution authority for the already
preregistered 24-cell V0.4 development study.

- authority id: `zec-v0-4-development-20260921-v0-1`
- authority is ineffective until explicit protected-main merge of PR #418;
- merge does not auto-dispatch;
- one later manual `workflow_dispatch` is the only execution path;
- one run / one attempt maximum; retry or rerun requires a new versioned authority;
- source is bounded to 48 public Binance Vision ZECUSDT 15m monthly archives plus 48 checksums;
- development remains `2022-08-01 <= t < 2026-08-01`;
- fresh confirmation remains unopened;
- aggregate-only report is allowed; raw candles and raw trades are not persisted;
- R2 / holdout / source switch / promotion / trade plan / real-money / live trading remain closed.


## ZEC V0.4 development completion

- One-shot development run `35618367238` completed successfully on main `dd12300b294f2a868389c49a877be97a41a3ebe8`.
- Full preregistered matrix completed: **6 candidates × 4 folds = 24/24 cells**.
- All 6 candidates satisfied the minimum trade-count gate.
- **0/6** candidates had positive worst-fold return.
- Selection result: **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**.
- No champion was frozen.
- Diagnostic leader `zec-v0-4-04` had worst-fold return `-8.12511401%`.
- The V0.4 bull-regime activation hypothesis did not establish cross-fold robustness.
- Fresh confirmation remains unopened.
- V0.3/V0.4 selection thresholds are not loosened from this outcome.
- R2 / holdout / source switch / promotion / trade plan / real-money / live trading remain closed.


## Reliability convergence through PR #423

The current protected-main reliability layer now includes three merged changes:

- PR #421: Research Signal Quality runs after successful Research Signal Layer completion on same-repository `main`, retains the 10:47 Asia/Taipei fallback, and uses exact immutable-run dedupe without opening R2 list/write authority.
- PR #422: Dashboard GitHub Pages validates the built site with pinned Playwright Chromium on desktop and mobile; production browser validation is gated on an actual Pages deployment.
- PR #423: Live Paper Coordinator V0.2 requires a deterministic atomic run-slot claim before any new provider call.

Live Paper run-slot details:

- Coordinator contract: `config/live_paper_run_coordinator_v0_2.json`.
- Claim contract: `config/live_paper_run_claim_v0_1.json`.
- Slot identity: `run_id + sequence + previous_step_id + previous_state_id`.
- R2 conditional create uses S3-compatible `IfNoneMatch="*"`; a 412/precondition conflict fails closed.
- Claim conflicts have no automatic retry, expiry or takeover.
- Recovery treats unresolved claims without a complete verified step as `REVIEW_REQUIRED`.
- Complete verified steps missing only the result seal remain repairable without provider access.
- Fully committed identical requests replay with zero new provider calls.
- Coordinator execution remains manual `workflow_dispatch` only; no schedule was added.
- Private exchange APIs, holdout access, real-money orders and real live trading remain closed.

PR #423 post-merge CI, CodeQL, Dashboard GitHub Pages and V0.10 Critical Path Freeze Guard all completed successfully.
