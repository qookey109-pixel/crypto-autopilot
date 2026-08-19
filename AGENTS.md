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
- Render is the current proven Mac-independent Binance public-metadata transport, but transport authority is not metadata-capture execution authority.
- Render must never receive R2 credentials. R2 credentials belong only in the authorized GitHub Actions/local secret boundary.
- Apply the FREE-ONLY operational R2 hard stop/headroom gate before future writes.

## V0.7 / V0.8 successor metadata boundary

- V0.7 Render metadata relay remains hard-disabled until a separate activation authority changes its code gate.
- V0.8 successor capture remains hard-disabled until a separate activation authority changes its execution gate.
- Do not enable a successor schedule while the V0.2 self-hosted schedule is still active.
- Old/new capture paths must never run concurrently; the future cutover must be atomic and explicitly versioned.
- The future shared `METADATA_RELAY_TOKEN` must be provisioned out of band in Render and GitHub Actions. Never commit or expose its value.
- Do not disable the currently authorized V0.2 metadata schedule merely because a successor scaffold exists; preparation is not activation.
- Replacement holdout candles remain forbidden during metadata capture and until a separate holdout-access authority exists.

## Evidence and change discipline

- Preserve passing tests and add tests for behavior changes.
- Frozen receipts/configs are historical evidence. Do not mutate them to make a later stage look successful; create a new versioned authority instead.
- Record strategy parameter changes in configuration and status docs.
- Record authority transitions in versioned configs/receipts and synchronize `PROJECT_STATUS.md`.
- Treat dashboards as normalized views, never as authority; generated dashboard state must be derived from frozen Repository authorities.
- Treat backtest results as evidence, not proof of future profitability.
- Prefer deterministic fixtures and fail-closed behavior for tests and automation.
- If an external dependency, free allowance, provider endpoint, secret, or runner is unavailable, fail closed rather than silently switching provider, endpoint, proxy, credentials, or paid tier.
