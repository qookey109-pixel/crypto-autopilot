# Current Operations Status

Updated: 2026-09-16

This is the concise current-operations entrypoint. Repository `main`, versioned configs/receipts, and immutable run evidence remain the formal authority. Dated prose in older status files is historical evidence, not a reason to regress an already completed lifecycle stage.

## Reviewed repository authority

- Repository: `qookey109-pixel/crypto-autopilot`
- Reviewed `main`: `f5cf74292fca262ba72c4e0b36f8d757dfb82531`
- Latest merged change: PR #321, `Treat bounds-only Pionex OHLC defects as historical boundary`.
- PR #321 merged exact reviewed head `880e3ed9203719cc992362918e3858a6dc63f5ec`.
- Merge-after CI passed on current `main`.

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

`.github/workflows/pionex-validation-materialization-v0-1.yml`

Current properties:

- manual `workflow_dispatch` only;
- public Pionex futures K-line reads only;
- validation-dataset R2 writes only;
- no API key or private-account data;
- no replacement holdout access;
- no training authorization;
- no source switch;
- no model promotion;
- no real-money orders;
- no live trading.

Previous authorized run `34991627998` failed closed on three structurally invalid `AAVE_USDT_PERP / 4H` candles. PR #321 now treats only finite, positive-price, non-negative-volume, non-inverted candles whose sole defect is OHLC high/low containment as a provider historical boundary; it does not fabricate or correct candles.

A new materialization run from current `main=f5cf7429...` is still required before claiming current-main Pionex validation completion.

## Current technical-debt focus

The largest current technical debt is **control-plane and documentation drift**, not a need to rewrite the trading/data core.

Priority order:

1. establish this single current-operations entrypoint plus a machine-readable companion;
2. project the same current truth into `README.md`, `PROJECT_STATUS.md`, `SECURITY.md`, and the Dashboard without rewriting frozen historical evidence;
3. triage open PRs against current `main` so stale branches cannot reintroduce superseded assumptions;
4. replace hard-coded workflow-count assumptions with an explicit active-workflow registry;
5. add non-blocking dependency/security/type/complexity visibility before considering stricter CI gates;
6. only after the operational control plane is stable, consider responsibility-splitting large modules such as `training/quality.py`.

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

Older September 13 present-tense summaries that report Core100 as `8/10` or Training as `SKIPPED` are historical observations and are superseded for current operations.

Do not use those older statements to restart History or classify current Training as incomplete.

Machine-readable companion: `research/status/current-operations-v0-2.json`.
