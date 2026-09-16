# Current Operations Status

Updated: 2026-09-16

This is the concise current-operations entrypoint. Repository `main`, versioned configs/receipts, and immutable run evidence remain the formal authority. Dated prose in older status files is historical evidence, not a reason to regress an already completed lifecycle stage.

## Repository authority semantics

- Repository: `qookey109-pixel/crypto-autopilot`.
- **Resolve `main` live at read time.** This file intentionally does not hard-code a claim that any SHA is the latest `main`.
- Evidence-basis parent main for this status version: `5eaf57133d013fad030681182b379a02d915766e`.
- Evidence-basis semantics: `REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION`.
- The evidence-basis SHA is **not** a latest-main claim; it records the reviewed parent from which this status version was prepared.
- PR #335 is the latest reviewed Pionex V0.2 materialization repair in that evidence basis; PR #322 remains the first control-plane/documentation convergence batch.

This avoids a self-reference bug where a file claiming its own future merge commit becomes stale immediately after it is merged.

## Current Core100 lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> Trading CLOSED`

### History

- Core100 detailed-history acquisition is complete: `10/10` governed shards.
- Historical reacquisition is **not required** solely because the model-quality gate rejected the trained model.
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
- completion evidence: `research/receipts/2026-09-16-pionex-validation-materialization-v0-2-pass.json`

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
- no live trading.

The materialization PASS does **not** override the Core100 **Model Quality REJECT** result and does not open Strategy Validation, Holdout, Promotion, or Trading.

## Current technical-debt focus

The largest current technical debt remains **control-plane and projection drift**, not a need to rewrite the trading/data core.

Already established by the first convergence batch:

- one current-operations human entrypoint;
- a machine-readable current-operations companion;
- root README / PROJECT_STATUS / SECURITY convergence;
- current-main PR triage;
- Research Automation Health count derived from exact schedule inventory instead of a hard-coded `7`.

Current cleanup priority:

1. production Dashboard must apply historical authority projection first and Current Operations projection last;
2. homepage present-tense state must derive from Current Operations rather than the dated September 13 simulation-readiness snapshot;
3. Dashboard / homepage must stop presenting the expired V0.12 window as an active execution path;
4. add non-blocking dependency/security/type/complexity visibility only after the control-plane projection is stable;
5. only after that consider responsibility-splitting large modules such as `training/quality.py`.

Detailed cleanup tracking lives in `docs/TECH_DEBT_REGISTER_2026_09_16.md`.

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

Older September 13 present-tense summaries that report Core100 as `8/10` or Training as `SKIPPED`, and older September 16 summaries that report Pionex validation as V0.1 / pending manual dispatch, are historical observations and are superseded for current operations.

Do not use those older statements to restart History, classify current Training as incomplete, or regress the completed Pionex V0.2 materialization stage.

Machine-readable companion: `research/status/current-operations-v0-3.json`.
