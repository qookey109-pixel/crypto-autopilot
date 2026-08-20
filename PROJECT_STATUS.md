# Project Status

Updated: 2026-08-20

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

Public dashboard: `https://qookey109-pixel.github.io/crypto-autopilot/`

Repository branch `main` is the live formal authority and is intentionally not self-pinned to a moving commit SHA in this file. Frozen receipts/configs remain immutable detailed evidence; this file is only the current status index.

## Current formal stage

**PIONEX M1/M1A PASS / M1B R2 PASS / BINANCE 2025 R2 PILOT PASS / BINANCE FUNDING V0.2 R2 MATERIALIZATION PASS / PIONEX-BINANCE EQUIVALENCE V0.1 DEFINITIVE FAIL / V0.5 RENDER FREE TRANSPORT PASS / V0.6 RENDER TRANSPORT TRANSITION PASS / V0.7 RENDER METADATA PROTOCOL HISTORICAL / V0.8 SHARED SECRET HANDSHAKE PASS FROZEN / V0.9 RENDER RELAY SMOKE PASS FROZEN / V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE / V0.2 SELF-HOSTED SCHEDULE RETIRED / V0.10 GITHUB-HOSTED SCHEDULE CURRENT / V0.11 METADATA STABILITY EVALUATOR PREPARED EXECUTION NOT_AUTHORIZED / REPLACEMENT HOLDOUT FROZEN_UNOPENED / METADATA STABILITY NOT_YET_RUN / HISTORICAL UNIVERSE MEMBERSHIP NOT_READY / TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED / PAPER-ONLY**

No live-money authorization exists. `trade_plan_authorized=false`, `real_money_order_authorized=false`, and `live_trading_authorized=false` remain mandatory.

## Current execution / transport authority

V0.10 activation merge commit from PR #127: `8fce944da479dbda0e2899f9b30b9de62351fa27`.

Current metadata-capture path:

- workflow: `.github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml`;
- runner: `ubuntu-latest`;
- Pionex metadata leg: GitHub-hosted direct public HTTPS;
- Binance USD-M metadata leg: authenticated Render Free / Frankfurt path `/metadata/v0-10/binance-exchange-info`;
- old V0.2 `[self-hosted, macOS, ARM64]` scheduled path: **RETIRED**;
- concurrent old/new metadata paths: forbidden;
- automatic fallback to V0.2: forbidden;
- Render receives R2 credentials: false.

Render remains FREE / Frankfurt. Current runtime budget is `0 USD/month`.

## Frozen metadata scope

Inherited scientific scope is unchanged:

- metadata capture: `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`;
- 194 UTC hourly slots;
- attempts at UTC `:17` and `:47`;
- current date-scoped schedules:
  - `17,47 * 27-31 8 *`
  - `17,47 * 1-3 9 *`
  - `17,47 0-1 4 9 *`
- 15 candidate symbols / 45 mapped pairs;
- replacement holdout: `2026-08-28T00:00:00Z` through `2026-09-03T23:59:59.999Z`;
- replacement holdout state: **FROZEN_UNOPENED**.

Each complete V0.10 capture uses 3 immutable run-scoped R2 objects. Receipt is written last, post-write SHA-256 readback is required, and every authorized write must pass a fresh whole-bucket 8,000,000,000-byte FREE-ONLY headroom gate.

No provider/R2 metadata capture is authorized outside the exact frozen window.

## V0.11 metadata stability evaluator — PREPARED ONLY

PR #131 froze the evaluator rules and implementation before production stability evidence is read.

Authorities:

- `config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json`
- `research/receipts/2026-08-20-provider-equivalence-v0-11-metadata-stability-evaluator-prepared.json`
- `src/crypto_autopilot/provider_metadata_stability_v0_11.py`
- `.github/workflows/validate-v0-11-metadata-stability-evaluator.yml`

Frozen evaluator semantics:

- require at least one complete valid V0.10 receipt for each of all 194 hourly slots;
- duplicate captures inside a slot are valid only if each provider's normalized 15-symbol vector matches exactly;
- Pionex and Binance USD-M vectors must each remain exactly stable across the entire capture window;
- missing slot, invalid receipt, normalized-vector SHA mismatch, same-slot disagreement, or cross-window drift => FAIL CLOSED;
- no post-hoc deadband, provider splicing, or symbol-scope shrink.

Current execution boundary:

- `V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED=false`;
- production R2 client construction/read is not authorized;
- production receipt listing/reading has not run under V0.11;
- provider and Render requests are not authorized by the prepared evaluator;
- raw provider objects and holdout objects may not be listed/read;
- metadata stability remains **NOT_YET_RUN**.

Even a future metadata-stability PASS will not itself authorize holdout access. A separate versioned holdout-access authority is required.

## Frozen historical results

### Pionex M1 / M1A — PASS

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- 15 frozen candidates;
- intervals `15M` / `60M` / `4H`;
- 13,230 candles;
- no gaps, duplicate timestamps, or invalid candles.

### M1B R2 — PASS

Authority: `research/receipts/2026-08-18-m1b-r2.json`

- 45 objects;
- 13,230 rows;
- 425,161 Parquet bytes;
- SHA-256 verified upload/download and exact candle round trip.

### Binance 2025 R2 pilot — PASS

Authority: `research/receipts/2026-08-18-binance-2025-r2-pilot.json`

- 528 source archives;
- 206 canonical R2 objects;
- 671,022 candles;
- provider remains `binance_usdm`;
- no Pionex-native relabeling authority.

### Funding V0.2 — PASS

Authorities:

- `research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-full-preflight.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json`

Result: 1,003 official source archives, 94 annual canonical objects, 192/192 authorized R2 identities verified, 91,747 Funding observations. HYPEUSDT 2026 remains deferred; no interpolation/provider splice is authorized.

### Equivalence V0.1 — DEFINITIVE FAIL

Authorities:

- `config/provider_equivalence_v0_1.json`
- `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json`
- `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1-direction-forensics.json`

Frozen result: 45 pairs = 18 PASS / 18 REVIEW / 9 FAIL. Direction forensics is descriptive only. `source_switch_authorized=false`. Thresholds/scope must not be changed after evidence to manufacture PASS.

### Render successor line — V0.5 through V0.10

Key authorities:

- `research/receipts/2026-08-19-provider-equivalence-v0-5-render-free-transport-pass.json`
- `research/receipts/2026-08-19-provider-equivalence-v0-6-render-transport-authority-transition.json`
- `config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json`
- `research/receipts/2026-08-19-provider-equivalence-v0-8-shared-relay-secret-handshake-pass.json`
- `research/receipts/2026-08-20-provider-equivalence-v0-9-render-relay-smoke-pass.json`
- `config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json`
- `research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json`

V0.8 remains **HISTORICAL** preparation evidence; it must not be rewritten to look like current V0.10 execution authority.

## Historical workflow retirement hygiene

Frozen proof/materialization evidence must not be routinely re-executed just because its historical workflow file still exists.

The following historical workflows are validation-only / `RETIRED_NO_EXECUTION`:

- `historical-backfill-pilot.yml`;
- `diagnose-v0-2-self-hosted-mac-binance-transport.yml`;
- `binance-2025-r2-pilot.yml`;
- `binance-vision-live-proof.yml`;
- `binance-vision-r2-proof.yml`;
- `binance-funding-r2-v0-2-preflight.yml`;
- `binance-funding-r2-v0-2-materialize.yml`;
- `m1b-m1a-dataset-upload.yml`;
- `m1b-r2-roundtrip.yml`.

They must have no schedule, no push-triggered production execution, no manual production rerun, no R2 secret binding, no self-hosted runner, and no real provider/materializer command. Reactivation requires a new versioned authority.

This retirement does not delete or invalidate their historical scripts/configs/receipts.

## Non-negotiable provider and safety boundaries

- Pionex remains execution target/provenance authority for Pionex-native evidence.
- Binance USD-M/Binance Vision remains provider-separated research evidence.
- Provider mapping never converts provenance.
- No provider splicing, silent interpolation, Pionex-native relabeling, or post-hoc provenance rewrite.
- V0.10 metadata authority is not strategy/backtest/trade/live authority.
- V0.11 prepared evaluator is not production stability authority.
- No staged Trade-Kline W1 materialization yet.
- Historical Universe membership remains NOT_READY.
- SState frozen core must not be modified by this phase.
- No martingale, loss doubling, unlimited averaging, or liquidation-as-stop.
- Public Binance `exchangeInfo` on this path uses no Binance API key; this is not a project-wide API-key ban. A future authenticated Binance scope needs separate authority and may not be used as a transport-blocker bypass.

## Current blockers

1. Metadata stability: production 194-slot evidence has not run yet.
2. Holdout access: replacement holdout is `FROZEN_UNOPENED` and requires separate authority after stability PASS.
3. Provider substitution: Equivalence V0.1 remains definitive FAIL.
4. Trade-Kline W1 materialization: NOT_AUTHORIZED.
5. Historical Universe membership: NOT_READY.
6. Strategy replay/backtest admission: still blocked by authority.
7. HYPE Funding 2026: deferred; no interpolation/provider splice.
8. Live execution: forbidden; project remains PAPER-ONLY.

## Next formal milestone

Before `2026-08-27T00:00:00Z`: readiness/maintenance validation only. Do not manually consume production metadata evidence.

During the frozen window:

1. Let the existing V0.10 schedule run at `:17/:47`.
2. Preserve the exact 194-slot / 15-symbol / 45-pair scope.
3. Keep the replacement holdout unopened.
4. Require the exact window/freshness gate and authenticated Render transport.
5. Require fresh R2 headroom before each write; never overwrite evidence.
6. After the full window, create a separate versioned V0.11 production evaluation authority **before any R2 receipt read for stability evaluation**.

## Explicitly forbidden next actions

- Do not manually run V0.10 production metadata capture before the frozen window.
- Do not manually run V0.11 production R2 stability evaluation under the prepared authority.
- Do not reactivate retired historical proof/materialization workflows without new authority.
- Do not re-enable the V0.2 self-hosted schedule or create a second concurrent metadata path.
- Do not access/evaluate replacement holdout candles.
- Do not alter Equivalence V0.1 thresholds/scope or add a post-hoc deadband.
- Do not source-switch, provider-splice, interpolate missing provider values, or relabel Binance evidence as Pionex-native.
- Do not expose relay/R2/exchange secrets in Repository, issues, logs, artifacts, tests, or chat.
- Do not give Render R2 credentials.
- Do not use third-party proxies, alternate endpoints, API keys, or a paid tier as a transport-blocker bypass.
- Do not authorize W1, strategy changes, automatic trade plans, real-money orders, or live trading.
