# Project Status

Updated: 2026-08-20

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

Public dashboard: `https://qookey109-pixel.github.io/crypto-autopilot/`

This file is the current project-status index. Frozen receipts, configs, documents, workflow artifacts and merged PRs remain the detailed authorities; this summary does not replace or rewrite historical evidence.

## Current formal stage

**PIONEX M1/M1A PASS / M1B R2 PASS / BINANCE 2025 R2 PILOT PASS / R2 BUDGET GATES PASS / BINANCE MAXIMUM-AVAILABLE COVERAGE DISCOVERY PASS / BINANCE FUNDING V0.2 R2 MATERIALIZATION PASS / FROZEN R2 INVENTORY 22.120404 MB / PIONEX-BINANCE EQUIVALENCE V0.1 DEFINITIVE FAIL / EQUIVALENCE V0.1 DIRECTION FORENSICS PASS / V0.2 SELF-HOSTED MAC BINANCE TRANSPORT PASS HISTORICAL / V0.5 RENDER FREE BINANCE TRANSPORT PASS / V0.6 RENDER TRANSPORT AUTHORITY TRANSITION PASS / V0.7 RENDER METADATA PROTOCOL HISTORICAL PREPARED / V0.8 SHARED RELAY SECRET HANDSHAKE PASS FROZEN / V0.8 SUCCESSOR RUNTIME PREPARED HISTORICAL / V0.9 AUTHENTICATED RENDER RELAY SMOKE PASS FROZEN / V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE / V0.2 SELF-HOSTED SCHEDULE RETIRED / V0.10 GITHUB-HOSTED SCHEDULE CURRENT / REPLACEMENT HOLDOUT FROZEN_UNOPENED / METADATA STABILITY NOT_YET_RUN / HISTORICAL UNIVERSE LONG-HORIZON REVIEW PASS / HISTORICAL UNIVERSE MEMBERSHIP NOT_READY / TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED / PAPER-ONLY**

Current `main` authority after PR #127 merge: `8fce944da479dbda0e2899f9b30b9de62351fa27`.

No live-money authorization exists. `trade_plan_authorized=false`, `real_money_order_authorized=false` and `live_trading_authorized=false` remain mandatory.

## Non-negotiable provider and safety boundaries

- **Pionex** remains the execution-target exchange and provenance authority for frozen Pionex-native evidence.
- **Binance USD-M / Binance Vision** remains provider-separated research evidence and always stays `provider=binance_usdm`.
- Symbol mapping such as `BTC_USDT_PERP <-> BTCUSDT` never converts provenance.
- Binance data must never be relabeled or written as Pionex-native data.
- Provider splicing, Pionex-native relabeling, silent interpolation and post-hoc provenance rewriting remain forbidden.
- `source_switch_authorized=false` remains binding after Equivalence V0.1 definitive FAIL.
- Frozen Equivalence V0.1 thresholds and 15-symbol / 45-pair scope must not be changed after evidence.
- V0.10 metadata-capture authority is metadata-only and is not strategy, backtest, trade-plan or live-trading authority.
- Replacement holdout candles remain forbidden until a separate post-stability holdout-access authority exists.
- No staged Trade-Kline wave is authorized for materialization yet.
- Historical Universe review PASS is not Historical Universe membership authority.
- SState frozen core must not be modified by these historical-data phases.
- No martingale, loss doubling, unlimited averaging or liquidation-as-stop is authorized.

## Frozen data and storage authorities

### Pionex M1 / M1A — PASS

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- 15-symbol frozen candidate universe: BTC, ETH, SOL, HYPE, ADA, BNB, UNI, XRP, LTC, LINK, DOGE, AAVE, AVAX, INJ, SUI.
- Intervals: `15M` / `60M` / `4H`.
- 13,230 candles.
- Zero gaps, zero duplicate timestamps and zero invalid candles.

### M1B Cloudflare R2 historical store — PASS

Authority: `research/receipts/2026-08-18-m1b-r2.json`

- Materialization run `32093154424` PASS.
- 45 objects / 13,230 rows / 425,161 Parquet bytes.
- Zstd Parquet, deterministic keys, SHA-256 upload/download verification and exact candle round-trip equality are frozen.

### Binance 2025 R2 content pilot — PASS

Authority: `research/receipts/2026-08-18-binance-2025-r2-pilot.json`

- 528 / 528 official source archives audited.
- 206 canonical Trade-Kline R2 objects.
- 671,022 candles.
- 18,778,928 Parquet bytes.
- 203 new objects uploaded; 3 pre-existing objects exact-verified without overwrite.
- Provider provenance remains Binance USD-M.

### R2 budget / frozen usage inventory — PASS

Authorities:

- `research/receipts/2026-08-18-r2-cost-budget.json`
- `research/receipts/2026-08-18-binance-observed-r2-budget.json`
- `research/receipts/2026-08-19-r2-bucket-usage.json`

Frozen read-only inventory evidence:

- 457 objects.
- 22,120,404 bytes = 22.120404 MB decimal.
- Inventory operation performed zero writes and zero deletes.

For V0.10 successor metadata work, the current operational FREE-ONLY hard stop is **8,000,000,000 bytes**. Every metadata write requires a fresh whole-bucket inventory/headroom check immediately before write. The older 22.120404 MB receipt remains historical inventory evidence and is not a substitute for that fresh prewrite check.

## Binance long-history foundation

### Maximum-available historical coverage discovery — PASS

Authority: `research/receipts/2026-08-18-binance-max-coverage-discovery.json`

- Project history floor: `2018-08`.
- Complete-month edge at evidence time: `2026-07`.
- 5,760 monthly checks: 4,040 AVAILABLE / 1,720 NO_DATA.
- 1,020 daily checks: 960 AVAILABLE / 60 NO_DATA.
- Coverage discovery itself does not authorize materialization, provider substitution, Historical Universe membership or source switching.

### Binance staged Trade-Kline expansion plan — PASS / MATERIALIZATION NOT_AUTHORIZED

Authority: `research/receipts/2026-08-18-binance-staged-expansion-plan.json`

Planned historical waves remain frozen as planning evidence:

- W1 2024: 14 symbols / 168 symbol-months / 504 source archives / 196 future R2 objects.
- W2 2023: 14 symbols / 164 symbol-months / 492 archives / 192 objects.
- W3 2022: 13 symbols / 149 symbol-months / 447 archives / 175 objects.
- W4 2021: 12 symbols / 144 symbol-months / 432 archives / 168 objects.
- W5 2020: 12 symbols / 104 symbol-months / 312 archives / 128 objects.

All waves remain `materialization_authorized=false`.

## Funding V0.2 — MATERIALIZATION PASS

Authorities:

- `research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-full-preflight.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json`

Formal result:

- workflow run `32168151926` SUCCESS.
- stage `BINANCE_FUNDING_R2_V0_2_MATERIALIZATION_PASS`.
- 1,003 official source archives.
- 94 annual canonical Parquet objects.
- 192 / 192 authorized R2 identities post-write verified.
- 91,747 Funding observations.
- 192 uploaded / 0 exact-existing in final execution.
- HYPEUSDT 2026 remains deferred because its source continuity issue was not repaired or interpolated.
- Source switch, provider splicing, Pionex relabeling, Historical Universe membership, backtest admission, trade-plan authorization and live trading remain false.

## Pionex ↔ Binance Equivalence V0.1 — DEFINITIVE FAIL

Protocol: `config/provider_equivalence_v0_1.json`

Authority: `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json`

Result document: `docs/PIONEX_BINANCE_EQUIVALENCE_V0_1_RESULT.md`

Definitive evidence run: `32206479914`.

- Execution status: PASS.
- Gate status: **FAIL**.
- Frozen overlap: `2026-08-10T08:00:00Z` through `2026-08-17T07:59:59.999Z`.
- 15 symbols / 3 intervals / 45 pairs.
- 18 PASS / 18 REVIEW / 9 FAIL.
- All 9 FAIL pairs contain `return_direction_agreement_fail`.
- `source_switch_authorized=false`.
- This result is permanent and must not be regraded by changing thresholds or scope after evidence.

## Equivalence V0.1 direction forensic — PASS / DESCRIPTIVE ONLY

Authority: `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1-direction-forensics.json`

- Frozen 45-pair result reproduced exactly at 18 PASS / 18 REVIEW / 9 FAIL.
- 623 total direction-mismatch bars.
- 539 / 623 mismatches were `ONE_PROVIDER_FLAT`; 84 were opposite non-zero signs.
- The evidence does not justify a post-hoc deadband or V0.1 regrade.
- V0.1 remains FAIL and source switching remains unauthorized.

## V0.2 historical metadata authority — TRANSPORT PASS / EXECUTION ROLE RETIRED

Historical authorities remain immutable:

- `research/receipts/2026-08-19-provider-equivalence-v0-2-transport-blocked.json`
- `research/receipts/2026-08-19-provider-equivalence-v0-2-self-hosted-mac-transport-pass.json`
- `research/receipts/2026-08-19-provider-equivalence-v0-2-forward-metadata-capture-authority-v0-2.json`
- `config/provider_equivalence_v0_2_metadata_capture_v0_2.json`

V0.2 established the replacement metadata scientific scope and proved Self-Hosted Mac transport. Those receipts remain valid historical evidence. However, PR #127 atomically retired the **scheduled V0.2 self-hosted execution path**; it is no longer the current metadata-capture scheduler and must not be silently reactivated as fallback.

The inherited scientific scope remains unchanged under V0.10:

- Replacement holdout: `2026-08-28T00:00:00Z` through `2026-09-03T23:59:59.999Z`, `FROZEN_UNOPENED`.
- Metadata capture window: `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`.
- 194 UTC hourly slots.
- Scheduled attempt minutes: `:17` and `:47`.
- 15 candidate symbols / 45 mapped pairs.
- Frozen provider price-increment semantics unchanged.

## Render / successor authority line — V0.5 PASS → V0.10 EFFECTIVE

Authorities:

- V0.5 transport PASS: `research/receipts/2026-08-19-provider-equivalence-v0-5-render-free-transport-pass.json`
- V0.6 transport transition PASS: `research/receipts/2026-08-19-provider-equivalence-v0-6-render-transport-authority-transition.json`
- V0.7 historical prepared protocol: `config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json`
- V0.8 prepared atomic contract: `config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json`
- V0.8 shared-secret PASS: `research/receipts/2026-08-19-provider-equivalence-v0-8-shared-relay-secret-handshake-pass.json`
- V0.8 successor runtime readiness: `research/receipts/2026-08-20-provider-equivalence-v0-8-successor-runtime-prepared.json`
- V0.9 authenticated relay smoke PASS: `research/receipts/2026-08-20-provider-equivalence-v0-9-render-relay-smoke-pass.json`
- V0.10 final cutover config: `config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json`
- V0.10 final cutover receipt: `research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json`

Current effective state:

- V0.5 Render Free / Frankfurt transport proof remains PASS with official Binance USD-M `exchangeInfo`, HTTP 200, valid JSON, `symbol_count=872`.
- V0.8 out-of-band `METADATA_RELAY_TOKEN` handshake is frozen PASS; the value was not recorded.
- V0.9 authenticated Render relay smoke is frozen PASS with exactly one provider request, HTTP 200, valid JSON, `symbol_count=872`, no raw persistence, no R2 and no holdout access.
- V0.8/V0.9 external proof workflows are regression-only and must not be routinely rerun.
- PR #127 merged at `8fce944da479dbda0e2899f9b30b9de62351fa27`, making V0.10 effective.
- Old V0.2 workflow has no schedule trigger and is historical validation-only.
- Current scheduled metadata workflow is `.github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml` on `ubuntu-latest`.
- Current V0.10 schedule is window-scoped:
  - `17,47 * 27-31 8 *`
  - `17,47 * 1-3 9 *`
  - `17,47 0-1 4 9 *`
- V0.10 Binance metadata transport uses authenticated Render Free / Frankfurt path `/metadata/v0-10/binance-exchange-info`.
- Historical V0.7 raw relay `/metadata/binance-exchange-info` remains disabled.
- Render service remains FREE / Frankfurt and must never receive R2 credentials.
- V0.10 scheduled runs are serialized; stale queued runs over 30 minutes fail closed before provider/R2 access.
- Every complete authorized metadata capture uses 3 immutable run-scoped R2 objects, receipt written last, post-write SHA-256 readback, and a fresh 8 GB whole-bucket headroom gate before write.
- No provider/R2 capture is authorized outside the exact frozen metadata window.

## Metadata stability — NOT_YET_RUN

This is the **current next scientific stage**.

Required evidence:

- At least one complete valid capture for every one of the 194 UTC hourly slots.
- Exact normalized 15-symbol provider vector stability across the full capture window under the frozen protocol.
- Any missing required hourly coverage or changed provider vector invalidates metadata applicability and must fail closed.
- The holdout stays unopened throughout metadata collection and stability review.

A future metadata stability PASS will still **not** authorize holdout candle access. A separate versioned holdout-access authority is required afterward.

## Historical Universe — REVIEW PASS / MEMBERSHIP NOT_READY

Authority: `research/receipts/2026-08-18-historical-universe-long-horizon-review.json`

- Long-horizon review prerequisite is satisfied for planned W1 scope: 2024 / 14 symbols / HYPE excluded.
- Formal membership remains NOT_READY.
- No Binance provider evidence may silently create Pionex-native membership.

## Dashboard

Fixed GitHub Pages site: `https://qookey109-pixel.github.io/crypto-autopilot/`

- Traditional Chinese: `zh-Hant-TW`.
- Dashboard JSON declares `authority=false`; it is a normalized view, never the authority itself.
- Current normalized view must show Equivalence V0.1 FAIL, Funding V0.2 PASS, V0.8/V0.9 frozen readiness evidence, V0.10 effective metadata cutover, metadata stability pending and replacement holdout unopened.
- `mode=PAPER-ONLY`.
- Metadata-capture authorization is explicitly distinct from `tradePlanAuthorized=false` and `liveTradingAuthorized=false`.

## Current blockers

1. **Metadata stability:** complete 194-slot evidence has not run yet; capture window begins `2026-08-27T00:00:00Z`.
2. **Holdout access:** replacement `2026-08-28` through `2026-09-03` holdout is `FROZEN_UNOPENED`; candle access/evaluation remains unauthorized until a separate authority after metadata stability PASS.
3. **Provider substitution/equivalence:** V0.1 is definitive FAIL; Binance cannot be substituted for Pionex provenance under that protocol.
4. **Trade-Kline W1:** 2024 materialization remains NOT_AUTHORIZED.
5. **Historical Universe membership:** NOT_READY until audited materialized partitions exist under an authorized path.
6. **Strategy replay admission:** blocked by authority and still-undefined full strategy-equivalence semantics.
7. **HYPE Funding 2026:** deferred; no interpolation or provider splice is authorized.
8. **Live execution:** forbidden; project remains PAPER-ONLY.

The former V0.8 activation, shared-secret provisioning and old/new exclusivity blockers are **resolved by frozen PASS evidence and the merged V0.10 atomic cutover**. They must not be reintroduced as current blockers.

## Next formal milestone

### Run frozen V0.10 metadata-stability capture — holdout remains unopened

No manual provider/R2 capture should be started before the frozen window. The scheduled workflow is already installed and date-scoped. The next action before `2026-08-27T00:00:00Z` is only readiness/status validation, not evidence consumption.

During the window:

1. Let the V0.10 schedule attempt captures at UTC minute `:17` and `:47` only on the date-scoped cron.
2. Preserve the exact 194-slot / 15-symbol / 45-pair scientific scope.
3. Require the exact window gate and 30-minute freshness guard before any provider/R2 access.
4. Require authenticated Render transport for the Binance metadata leg and direct public Pionex metadata transport.
5. Require fresh whole-bucket R2 inventory and the 8 GB hard stop before every metadata write.
6. Keep keys immutable and run-scoped; never overwrite existing evidence; write receipt last and verify SHA-256 by readback.
7. Keep replacement holdout candles unopened and unevaluated.
8. After the full window, build a separate metadata-stability result authority. Do not infer PASS from partial coverage.

## Explicitly forbidden next actions

- Do not manually run production metadata capture before the frozen metadata window.
- Do not re-enable the retired V0.2 self-hosted schedule or create a second concurrent metadata-capture path.
- Do not use V0.2 as automatic fallback if V0.10 transport fails.
- Do not access or evaluate replacement holdout K-lines before a separate holdout-access authority exists.
- Do not lower or alter Equivalence V0.1 thresholds or shrink its frozen scope to manufacture PASS.
- Do not reinterpret descriptive V0.1 forensic bins as gate thresholds or add a post-hoc deadband.
- Do not source-switch, provider-splice, interpolate missing provider values, or relabel Binance data as Pionex-native.
- Do not put `METADATA_RELAY_TOKEN`, R2 credentials, exchange secrets or other secret values in Repository, issues, logs, artifacts or chat.
- Do not give Render R2 credentials.
- Do not retry retired Cloudflare Container V0.3 or superseded Koyeb V0.4 as this path's fallback.
- Do not use a third-party proxy, alternate endpoint or Binance API key as a transport-blocker bypass.
- This does **not** declare a project-wide Binance API-key ban; future authenticated Binance functionality requires its own versioned authority/security boundary.
- Do not upgrade Render or another runtime to a paid plan or add a payment method for this FREE-ONLY path.
- Do not authorize W1 merely because storage capacity exists.
- Do not change SState frozen core for this phase.
- Do not authorize strategy parameter changes, automatic trade plans, real-money orders or live trading.
