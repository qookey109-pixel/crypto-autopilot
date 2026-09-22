# Current Operations Status

Updated: 2026-09-22

This is the concise current-operations entrypoint. Repository `main`, versioned configs/receipts, and immutable run evidence remain the formal authority. Dated prose in older status files is historical evidence, not a reason to regress an already completed lifecycle stage.

## Repository authority semantics

- Repository: `qookey109-pixel/crypto-autopilot`.
- **Resolve `main` live at read time.** This file intentionally does not hard-code a claim that any SHA is the latest `main`.
- Evidence-basis parent main for this status version: `9ffe30c8f0ab28bc3b2a95ae19de6938ed613dae`.
- Evidence-basis semantics: `REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION`.
- The evidence-basis SHA is **not** a latest-main claim; it records the reviewed parent from which this status version was prepared.
- The current open-PR navigation has been refreshed to V0.7 from reviewed main after PR #448; the navigation snapshot records zero open pull requests while the evidence-basis SHA remains historical review context rather than a future latest-main claim.

This avoids a self-reference bug where a file claiming its own future merge commit becomes stale immediately after it is merged.

## Current Core100 lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> REAL TRADING CLOSED / LIVE-PAPER SEPARATELY AUTHORIZED`

### History

- Core100 detailed-history acquisition is complete: `10/10` governed shards.
- Historical reacquisition is **not required** solely because the model-quality gate rejected the trained model.
- The automatic History cron and generic auto/discover/backfill entrypoints are retired; only existing bounded diagnosis/repair modes remain.
- Do not restart the History program unless new evidence identifies an actual dataset-integrity failure.

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
- run window: `2026-09-15T01:40:40Z` through `2026-09-15T04:38:22Z`

Operational training success does **not** mean the model passed research quality gates.

Weekly Training remains scheduled, but it now compares the governed dataset
fingerprint plus model-affecting Git blobs before full training. An exact match
returns `NO_CHANGE`, performs no retraining and writes nothing to R2. The
verified baseline is run `34918219864` with experiment fingerprint
`25b3178ce0d13052684d20b35a0e1f6949f0d97a5ac0c5b9e8f0a52d4d12f9c8`.

### Model-quality gate and threshold replay

Current model-quality outcome: **REJECT**.

- fold-1 is the only fold identified as failing the naive log-loss comparison.
- configured probability threshold `0.55` emitted zero signals in all four folds.
- automatic promotion remains disabled.

Exact read-only threshold replay run: `34936331199`

- workflow conclusion: `success`
- exact run head: `fbebb5cbe424e4a6d6c33cb6e09a12da4849ee07`
- dataset fingerprint preserved: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`
- artifact: `10387278663`
- artifact digest: `sha256:f983f5364024a911be3f930fce641bd750922a8d95e710951b88d5738f5cfa29`
- thresholds evaluated: `0.50` through `0.55`
- `supported_thresholds = []`
- `threshold_change_supported = false`
- configured threshold remains unchanged.

Replay interpretation:

- `0.50`: fold-1 negative, fold-2 positive, fold-3/4 zero signal.
- `0.51`: fold-1/2 negative, fold-3/4 zero signal.
- `0.52` through `0.55`: zero signals in all folds.

Do not loosen the quality gate or change the configured threshold without a separately reviewed versioned decision.

## Pionex validation state

Pionex remains the final calibration / execution-environment provenance target, while Binance USD-M remains the large-scale learning database. Evidence from the two providers must remain provenance-separated.

Current validation workflow:

`.github/workflows/pionex-validation-materialization-v0-2.yml`

Current materialization result: **COMPLETE / PASS**.

- workflow run: `35054729471`
- workflow head: `5eaf57133d013fad030681182b379a02d915766e`
- report status: `PASS`
- report stage: `PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_2`
- selected markets: `197`
- partitions: `682`
- provider requests: `1,534`
- manifest: `market-data/pionex/validation-dataset-v0.2/runs/run=github-35054729471-1/manifest.json`
- manifest SHA-256: `192eddd1c69dd435d2ea12a0bf68e05e1cbc1a0fd512f4321f631755c61ca225`
- artifact: `10430054351`
- artifact digest: `sha256:5f8c3406ee5dc9a491cd800241c1cc7e2dd66bc98fa292da1c8bb05535dede55`
- R2 latest pointer written last: `true`
- complete 197-market multiyear history claimed: `false`
- Core100 Pionex training performed: `false`
- completion evidence: `research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json`

V0.2 preserves explicit incomplete-coverage states rather than fabricating history. This PASS means the frozen 197-market / 682-partition validation materialization contract completed successfully; it does **not** mean every market has complete multiyear history.

Current authority boundaries remain unchanged:

- manual `workflow_dispatch` only for the governed materialization path;
- public Pionex futures K-line reads only;
- validation-dataset R2 writes only;
- no API key or private-account data;
- no replacement holdout access;
- no training authorization;
- no source switch;
- no model promotion;
- no formal trade plan;
- no real-money orders;
- no real live trading.

Separate from those validation gates, Live Paper Simulation V0.1 authorizes public live Pionex market data plus simulated paper execution/account updates only. It does not use private account/order endpoints.

The materialization PASS does **not** override the Core100 **Model Quality REJECT** result and does not open Strategy Validation, Holdout, Promotion, or Trading.

## Current technical-debt focus

The prior control-plane/dashboard projection drift is now substantially converged. The main cleanup focus has moved to **backlog hygiene plus non-blocking quality/dependency/security visibility**, not a rewrite of the trading/data core.

Already established and verified:

- one current-operations human entrypoint and machine-readable companion;
- root README / PROJECT_STATUS / SECURITY convergence;
- production Dashboard applies historical authority first and Current Operations last;
- homepage present-tense state derives from Current Operations rather than the dated September 13 simulation-readiness snapshot;
- expired V0.12 execution state is historical, not current;
- Pionex V0.2 materialization completion is converged into current status/projections;
- immutable Core100 REJECT / threshold-replay evidence is preserved on `main`;
- Research Automation Health count derives from exact schedule inventory rather than a hard-coded `7`;
- Repository retains eight cron declarations and Health monitors all eight; seven are current-effective, while the frozen V0.12 declaration is expired and window-gated. Dashboard projects only the seven effective jobs;
- CI emits non-blocking quality and semantic type visibility artifacts on Python 3.13;
- CodeQL provides non-blocking repository-controlled security visibility;
- Dependabot provides monthly review-only visibility for `pip` and GitHub Actions.

Current cleanup priority:

1. keep the open-PR triage aligned with current `main` and do not merge stale architecture-generation branches directly;
2. review dependency PRs independently, with extra compatibility scrutiny for major-version jumps;
3. follow `docs/TYPE_DEBT_BASELINE_2026_09_22.md`: reduce non-execution dynamic-object type debt first, without blanket `Any` / `type: ignore`, before considering any required type gate;
4. treat #302/#315/#306/#307 as closed historical salvage only; rebuild selected ideas from current `main` only if deliberately revived;
5. review the 261-error mypy baseline by category before considering any blocking type gate;
6. only after that consider responsibility-splitting large modules such as `training/quality.py`.

Detailed cleanup tracking lives in `docs/TECH_DEBT_REGISTER_2026_09_17.md`. Type-debt baseline tracking lives in `docs/TYPE_DEBT_BASELINE_2026_09_22.md` with machine-readable companion `research/status/type-debt-baseline-v0-1.json`.
Current open-PR navigation lives in `docs/OPEN_PR_TRIAGE_2026_09_22.md` with machine-readable companion `research/status/open-pr-triage-v0-7.json`. The reviewed open backlog is zero after the #326–#331 dependency review and current-main rebuilds #445/#447/#448; older architecture-generation and salvage PRs remain historical references.

## Safety and governance still binding

- Current mode: **PAPER / LIVE-PAPER ONLY**.
- Public live market data + live paper simulation: authorized only under `config/live_paper_simulation_v0_1.json`.
- Private exchange APIs, real-money orders and real live trading: **CLOSED**.
- `source_switch_authorized=false`.
- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- Pionex-native and Binance USD-M evidence must remain provenance-separated.
- Project cloud/runtime budget remains `0 USD/month` for the FREE-ONLY path.
- Render must never receive R2 credentials.
- Secrets must never be committed, logged, artifacted, or pasted into chat.
- Frozen historical evidence must not be rewritten to make a later stage appear successful.

## Documentation drift rule

Older September 13 present-tense summaries that report Core100 as `8/10` or Training as `SKIPPED`, and older September 16 summaries that report Pionex validation as V0.1 / pending manual dispatch, are historical observations and are superseded for current operations.

Do not use those older statements to restart History, classify current Training as incomplete, or regress the completed Pionex V0.2 materialization stage.

Machine-readable companion: `research/status/current-operations-v0-3.json`.

- Dashboard cloud monitoring V0.2 is prepared as metadata-only execution evidence; workflow success is not a business-result claim.


## ZEC Strategy V0.3 development result

The one-shot governed development run is complete.

- workflow run: `35573236145`
- run attempt: `1`
- execution head: `c33c81732deae569fb924f61f81868a128690a07`
- workflow conclusion: **SUCCESS**
- artifact: `10626687807`
- artifact digest: `sha256:61bb133d9751aef381010d504250bb51c2e224f087344cb7f974396845c7cc90`
- report SHA-256: `7428a8ced8cc401a98f061de7c77a54650dc53eb660443ec947f09e8e5fd2321`
- development matrix: **256 / 256 COMPLETE**
- selection result: **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**
- champion frozen: **false**
- all 64 candidates met the minimum 30 realized trades per fold
- candidates with positive worst-fold return: **0 / 64**

The diagnostic leader is `zec-v0-3-45`, but it is **not** a selected champion.
Its worst-fold return is `-8.12511401%`; the four development-fold returns are
`-6.00733290%`, `-8.12511401%`, `-0.07906656%`, and `+6.28084212%`.

Therefore the blocking gate is cross-fold robustness, not trade count.
The frozen selection threshold is not loosened or retuned from this outcome.

Fresh confirmation remains unopened. No holdout, R2, source switch, promotion,
formal trade plan, real-money order, or live trading authority is opened by
this execution result.

Completion receipt:
`research/receipts/2026-09-21-zec-v0-3-development-completion-v0-1.json`


## ZEC Strategy V0.4 preregistration

V0.3 remains complete with `NO_ELIGIBLE_DEVELOPMENT_CANDIDATE`; its frozen
selection policy is not relaxed.

V0.4 prepares a new **contract-only** regime-activation hypothesis:

- development history remains the already-seen `2022-08-01 <= t < 2026-08-01`;
- fresh confirmation `2026-08-01 <= t < 2026-09-16` remains unopened;
- 2 MACD variants × 3 causal 4h activation regimes = **6 candidates**;
- 4 chronological folds = **24 development cells**;
- ATR extreme guard, 2.5ATR/Bollinger stop and 1% account risk are fixed rather
  than swept;
- V0.3 frozen selection policy is reused unchanged;
- execution authority: **false**;
- provider / R2 / holdout / source switch / promotion / trading authority:
  **false**.

Aggregate V0.3 diagnosis:
`research/receipts/2026-09-21-zec-v0-3-development-diagnostic-v0-1.json`

V0.4 contract:
`config/zec_strategy_v0_4_development_matrix_v0_1.json`


## ZEC Strategy V0.4 one-shot development authority

PR #418 prepares the reviewed execution surface for the preregistered V0.4
development matrix.

- authority id: `zec-v0-4-development-20260921-v0-1`
- authority state before merge: **INEFFECTIVE**
- effective condition: explicit protected-main merge of PR #418
- merge auto-starts execution: **false**
- subsequent dispatch mode: **manual workflow_dispatch only**
- maximum runs: **1**
- maximum run attempts: **1**
- development matrix: **6 candidates × 4 folds = 24 cells**
- public source: Binance USD-M / Binance Vision monthly ZECUSDT 15m
- source months: `2022-08` through `2026-07`
- maximum source requests: **96** (48 archives + 48 checksums)
- raw candles persisted: **false**
- raw trade artifact: **false**
- aggregate report artifact: **allowed only after authority becomes effective**

The merge itself does not execute the study. A first manual dispatch consumes
the one-shot authority; a failed or cancelled first attempt is not rerunnable
under the same authority.

Fresh confirmation remains unopened. R2, formal holdout, source switch,
promotion, formal trade plans, real-money orders and live trading remain closed.

Authority receipt:
`research/receipts/2026-09-21-zec-v0-4-development-one-shot-authority.json`


## ZEC Strategy V0.4 development result

The governed V0.4 one-shot development run is complete.

- workflow run: `35618367238`
- run attempt: `1`
- execution head: `dd12300b294f2a868389c49a877be97a41a3ebe8`
- workflow conclusion: **SUCCESS**
- artifact: `10647816808`
- artifact digest: `sha256:ea9c7652d98fdf947216fc4f291b8823b99fa66e8b210d279b58be615da846de`
- report SHA-256: `764a3667dcbc91a7142b2b2bf3fdd33c0051492ba1b892fb6283e05148c09959`
- development matrix: **24 / 24 COMPLETE**
- selection result: **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**
- champion frozen: **false**
- all 6 candidates met the minimum 30 realized trades per fold
- candidates with positive worst-fold return: **0 / 6**

Diagnostic leader only:
- `zec-v0-4-04`
- MACD `12/30/7`
- activation regime `TREND_STRICT_BASELINE`
- worst-fold return `-8.12511401%`
- median-fold return `-3.04319973%`
- fold returns `-6.00733290%`, `-8.12511401%`, `-0.07906656%`, `+6.28084212%`

The stricter stacked / momentum activation variants improved some later-period
results but did not establish positive worst-fold return. V0.4 therefore does
not open fresh confirmation and does not justify relaxing the frozen selection
policy.

Fresh confirmation, R2, formal holdout, source switch, promotion, formal trade
plans, real-money orders and live trading remain closed.

Completion receipt:
`research/receipts/2026-09-21-zec-v0-4-development-completion-v0-1.json`


## Automation reliability convergence — PR #421 / #422 / #423

The second reliability batch is now merged and verified on protected `main`.

### Research Signal Quality

PR #421 merged upstream-completion chaining for `Research Signal Layer V0.2` while preserving the existing daily 10:47 Asia/Taipei fallback.

- workflow-run execution requires successful same-repository `main` lineage;
- previous successful secret-free Quality evidence may be reused only when `run_id + manifest_sha256 + generated_at_utc` match exactly;
- an exact verified match returns `NO_CHANGE`, rechecks freshness and reads only `latest.json`;
- any identity mismatch falls back to the full three-object lineage verification;
- R2 list/write authority remains false.

### Dashboard browser QA

PR #422 merged pinned Playwright Chromium validation.

- Chromium only, one worker;
- desktop and mobile profiles;
- PR validation runs against the built `_site`;
- production browser validation runs only after a real GitHub Pages deploy;
- screenshots and traces are retained only on failure for 7 days;
- the latest merged PR path passed desktop/mobile browser validation before merge.

### Live Paper Run Slot Claim V0.1

PR #423 is merged and current.

- Coordinator contract: `config/live_paper_run_coordinator_v0_2.json`.
- Claim contract: `config/live_paper_run_claim_v0_1.json`.
- One deterministic slot binds `run_id + sequence + previous_step_id + previous_state_id`.
- The slot is created atomically with R2/S3-compatible `IfNoneMatch="*"` before a new provider call.
- A claim conflict performs no automatic retry, expiry or takeover.
- Recovery returns `REVIEW_REQUIRED` for unresolved claims without a complete verified matching step.
- A complete verified step with only a missing result seal remains eligible for provider-free seal repair.
- Existing fully committed identical requests replay with zero new provider requests.
- The coordinator remains explicit `workflow_dispatch` only; no cron schedule was added.
- Private exchange APIs, holdout access, real-money orders and real live trading remain closed.

Post-merge verification for PR #423 completed successfully: CI, CodeQL, Dashboard GitHub Pages and V0.10 Critical Path Freeze Guard all passed.
