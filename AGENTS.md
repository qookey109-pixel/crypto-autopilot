# Agent Instructions

## Source of truth

Read these first, in order:

1. `PROJECT_STATUS.md`
2. `README.md`
3. the current versioned protocol/config and receipt for the stage being changed
4. `config/cloud_free_tier_policy_v0_1.json` for cloud/runtime work
5. `docs/STRATEGY_V0_1.md`
6. `config/strategy_v0_1.json`

Repository `main` is the formal current authority. If chat history, an issue comment, a dashboard fixture, or an older receipt conflicts with current merged authority, preserve the historical evidence but follow the latest valid versioned authority for new work.

## Non-negotiable boundaries

- Do not enable live trading or real-money orders without a separate explicit versioned authority.
- Do not add, commit, print, log, or request secret values in issues, pull requests, artifacts, tests, fixtures, or chat.
- Do not rewrite the validated SState core; integrate through the adapter only.
- Pionex is the execution target/provenance authority for Pionex-native evidence, not the architecture itself.
- Binance USD-M/Binance Vision evidence remains provider-separated and must never be relabeled as Pionex-native.
- `source_switch_authorized=false` remains binding after Equivalence V0.1 definitive FAIL.
- Do not change frozen Equivalence V0.1 thresholds or scope after evidence.
- Keep strategy, risk, portfolio, persistence and exchange execution separable.
- Do not force a fixed number of daily trades.
- Do not introduce martingale, loss-doubling or unlimited averaging down.
- Do not increase leverage above the configured cap without a new version and explicit validation.

## FREE-ONLY cloud discipline

- Project runtime budget is `0 USD/month`.
- Do not upgrade Render, Cloudflare, or another runtime to a paid plan for this path.
- Do not add a payment method as a fallback mechanism.
- Cloudflare Containers are retired/blocked for this project; do not revive or retry that route.
- Koyeb V0.4 is superseded; do not restore it as an active candidate without a new authority.
- Render Free / Frankfurt is the current proven Binance public-metadata transport leg.
- Render must never receive R2 credentials. R2 credentials belong only in the authorized GitHub Actions/local secret boundary.
- Apply the FREE-ONLY operational R2 hard stop/headroom gate before every authorized metadata write.
- Historical workflows whose proof/materialization is already frozen must remain validation-only. Do not reintroduce schedule, push execution, provider requests, self-hosted execution, R2 secret bindings, or write commands without a new versioned authority.

## V0.10 historical metadata-capture authority

- PR #127 is merged on `main`; V0.10 final atomic metadata-capture cutover is **effective**.
- Current cutover authority: `config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json` and `research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json`.
- V0.10 is historical effective authority whose remaining schedule is retired by
  the reviewed V0.12 successor transition. Its workflow has no schedule and
  cannot be used for manual capture, replay or backfill.
- Historical V0.2 `[self-hosted, macOS, ARM64]` scheduled metadata execution is retired. Preserve its receipts and transport PASS as immutable historical authority; do not silently reactivate it or use it as automatic fallback.
- Historical V0.7 raw relay `/metadata/binance-exchange-info` remains disabled. Current V0.10 versioned relay path is `/metadata/v0-10/binance-exchange-info`.
- V0.8 prepared cutover/scaffold remains frozen historical evidence. Do not mutate V0.8 receipts/configs to describe the V0.10 effective state.
- V0.8 shared-secret handshake and V0.9 relay smoke are frozen PASS evidence and their workflows are regression-only; do not rerun external handshake/smoke routinely.
- `METADATA_RELAY_TOKEN` is already an out-of-band shared secret between Render and GitHub Actions. Never commit, expose, rotate, or request its value unless a separately authorized security operation requires rotation.
- Exact metadata capture window remains `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`, 194 UTC hourly slots with `:17/:47` attempts.
- V0.10 metadata capture is metadata-only. It authorizes provider metadata fetch plus metadata-only immutable R2 writes inside the frozen window, subject to the fresh 8 GB headroom gate.
- Preserve all V0.10 failures and missing slots without replay, backfill or
  regrading. Do not re-enable V0.10 or V0.2 scheduling.

## V0.12 successor metadata-capture authority

- The successor authority is
  `config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json` with
  receipt
  `research/receipts/2026-08-31-provider-equivalence-v0-12-successor-metadata-window-authority.json`.
- On the exact protected-main merge, V0.12 is the only scheduled metadata
  capture workflow:
  `.github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml`.
- Its exact window is `2026-09-04T02:00:00Z` through
  `2026-09-12T03:59:59.999Z`, 194 UTC hourly slots with `:17/:47` attempts.
- It reuses the existing authenticated V0.10 Render raw relay without changing
  Render code, deployment or secrets. Render still must never receive R2
  credentials.
- V0.12 may write metadata-only immutable objects only in its independent R2
  namespace and only after the fresh 8 GB FREE-ONLY headroom gate.
- Pionex `contractType/status` and legacy `type/enable` representations are
  accepted only under the frozen agreement rules. Missing, unknown or
  conflicting representations fail closed before R2 client construction.
- V0.12 production R2 stability evaluation is not authorized. It requires a
  separate post-window versioned authority, and even a future PASS does not
  authorize holdout candle access.

## V0.11 metadata-stability evaluator preparation

- PR #131 froze the deterministic V0.11 evaluator before production stability evidence is read.
- Current files: `config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json`, `research/receipts/2026-08-20-provider-equivalence-v0-11-metadata-stability-evaluator-prepared.json`, and `src/crypto_autopilot/provider_metadata_stability_v0_11.py`.
- V0.11 is **PREPARED**, not a metadata-stability PASS.
- `V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False` remains binding until a separate post-window execution authority exists.
- Do not construct an R2 client, list or read production V0.10 receipts, or automatically evaluate the production window under the prepared authority.
- Synthetic validation is allowed and must preserve the frozen 194-slot rules: complete hourly coverage, exact within-slot duplicate agreement, and exact cross-window provider-vector stability.
- Missing slots, invalid receipts, normalized-vector SHA mismatch, same-slot disagreement, or cross-window vector drift must fail closed.
- V0.11 may never list/read raw provider objects or replacement holdout objects under its prepared authority.
- A future metadata-stability PASS still does not authorize holdout candle access; that requires a separate versioned authority.

## Holdout and scientific boundary

- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- Metadata capture does **not** authorize holdout candle access or evaluation.
- Metadata stability is `NOT_YET_RUN` until complete 194-slot evidence is collected and reviewed under a separately authorized V0.11 production evaluation stage.
- Even a future metadata stability PASS does not itself authorize holdout candles; a separate versioned holdout-access authority is required.
- W1 materialization, Historical Universe membership, backtest admission, strategy parameter changes, automatic trade plans, real-money orders and live trading remain unauthorized.
- Public Binance `exchangeInfo` used by this metadata path does not require an API key. This is not a project-wide Binance API-key ban; API keys may be used by a future separately versioned authenticated Binance scope, but never as a transport-blocker bypass.

## Evidence and change discipline

- Preserve passing tests and add tests for behavior changes.
- Frozen receipts/configs are historical evidence. Do not mutate them to make a later stage look successful; create a new versioned authority instead.
- Record strategy parameter changes in configuration and status docs.
- Record authority transitions in versioned configs/receipts and synchronize `PROJECT_STATUS.md`.
- Treat dashboards as normalized views, never as authority; generated dashboard state must be derived from frozen Repository authorities.
- Treat backtest results as evidence, not proof of future profitability.
- Prefer deterministic fixtures and fail-closed behavior for tests and automation.
- If an external dependency, free allowance, provider endpoint, secret, or runner is unavailable, fail closed rather than silently switching provider, endpoint, proxy, credentials, or paid tier.
