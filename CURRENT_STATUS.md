# Current Operations Status

Updated: 2026-09-21

This is the concise current-operations entrypoint. Repository `main`, versioned configs/receipts, and immutable run evidence remain the formal authority. Dated prose in older status files is historical evidence, not a reason to regress an already completed lifecycle stage.

## Repository authority semantics

- Repository: `qookey109-pixel/crypto-autopilot`.
- **Resolve `main` live at read time.** This file intentionally does not hard-code a claim that any SHA is the latest `main`.
- Evidence-basis parent main for this status version: `3422efc91cfd973ab1991080186fb8300d26a2a5`.
- Evidence-basis semantics: `REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION`.
- The evidence-basis SHA is **not** a latest-main claim; it records the reviewed parent from which this status version was prepared.
- PR #410 is the latest reviewed merge in that evidence basis; it established Resource Hub V0.2 change-watch and dashboard schedule/source projection.

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
- current Repository cron inventory is seven workflows after the expired V0.12 successor cron retirement; Dashboard/Health/Automatic Operations must match it exactly;
- CI emits a non-blocking quality-visibility artifact on Python 3.13;
- Dependabot provides monthly review-only visibility for `pip` and GitHub Actions.

Current cleanup priority:

1. keep the open-PR triage aligned with current `main` and do not merge stale architecture-generation branches directly;
2. review dependency PRs independently, with extra compatibility scrutiny for major-version jumps;
3. add non-blocking type/security visibility before considering any new required quality gate;
4. review only still-unique code hardening from PR #302 and still-useful data-role governance from PR #315 against current `main`;
5. rebuild #306/#307 from current main only if those capabilities remain priorities;
6. only after that consider responsibility-splitting large modules such as `training/quality.py`.

Detailed cleanup tracking lives in `docs/TECH_DEBT_REGISTER_2026_09_17.md`.
Current open-PR navigation lives in `docs/OPEN_PR_TRIAGE_2026_09_17.md` with machine-readable companion `research/status/open-pr-triage-v0-4.json`.

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
