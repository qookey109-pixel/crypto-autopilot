# Project Status

Updated: 2026-08-19

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

Public dashboard: `https://qookey109-pixel.github.io/crypto-autopilot/`

This file is the current project-status index. Frozen receipts, configs, documents, workflow artifacts and merged PRs remain the detailed authorities; this summary does not replace them.

## Current formal stage

**PIONEX M1/M1A PASS / M1B R2 PASS / BINANCE 2025 R2 PILOT PASS / R2 BUDGET GATES PASS / BINANCE MAXIMUM-AVAILABLE COVERAGE DISCOVERY PASS / BINANCE FUNDING V0.2 R2 MATERIALIZATION PASS / R2 LIVE USAGE 22.120404 MB / PIONEX-BINANCE EQUIVALENCE V0.1 FAIL / EQUIVALENCE V0.1 DIRECTION FORENSICS PASS / V0.2 SELF-HOSTED MAC BINANCE TRANSPORT PASS / V0.2 REPLACEMENT METADATA CAPTURE AUTHORIZED / V0.5 RENDER FREE BINANCE TRANSPORT PASS / V0.6 RENDER TRANSPORT AUTHORITY TRANSITION PASS / V0.7 RENDER METADATA CAPTURE PROTOCOL PREPARED EXECUTION_NOT_AUTHORIZED / V0.2 REPLACEMENT HOLDOUT FROZEN_UNOPENED / METADATA STABILITY NOT_YET_RUN / HISTORICAL UNIVERSE LONG-HORIZON REVIEW PASS / HISTORICAL UNIVERSE MEMBERSHIP NOT_READY / TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED / STRATEGY REPLAY READINESS GATE BLOCKED ON AUTHORITY / PAPER-ONLY**

No live-money authorization exists. `trade_plan_authorized=false` and `live_trading_authorized=false` remain mandatory.

## Non-negotiable provider and safety boundaries

- **Pionex** remains the execution-target exchange and the provenance authority for frozen Pionex-native evidence.
- **Binance USD-M / Binance Vision** remains a provider-separated research-history source and always stays `provider=binance_usdm`.
- Symbol mapping such as `BTC_USDT_PERP <-> BTCUSDT` never converts provenance.
- Binance data must never be relabeled or written as Pionex-native data.
- Provider splicing, Pionex-native relabeling and silent interpolation remain forbidden.
- `source_switch_authorized=false` after the definitive Equivalence V0.1 FAIL.
- Frozen Equivalence V0.1 scope and thresholds must not be changed after evidence.
- No staged Trade-Kline wave is authorized for materialization yet.
- Historical Universe review PASS is not Historical Universe membership authority.
- Backtest framework readiness is not backtest-admission authority.
- SState frozen core is not modified by these historical-data phases.
- No martingale, loss doubling or unlimited averaging is authorized.
- Real-money orders and live trading remain forbidden.

## Frozen data and storage authorities

### Pionex M1 / M1A — PASS

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- 15-symbol frozen candidate universe: BTC, ETH, SOL, HYPE, ADA, BNB, UNI, XRP, LTC, LINK, DOGE, AAVE, AVAX, INJ, SUI.
- `15M` / `60M` / `4H`.
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

### R2 budget — PASS

Authorities:

- `research/receipts/2026-08-18-r2-cost-budget.json`
- `research/receipts/2026-08-18-binance-observed-r2-budget.json`

Observed 2025 basis:

- 671,022 rows / 18,778,928 bytes.
- 250 markets x 8 years canonical projection: about 2.574 GB.
- Canonical + retained staging: about 5.148 GB.
- 3x storage stress: about 7.722 GB.
- Existing storage BLOCK guardrail remains 10 GB.

### Current live R2 usage — PASS / READ-ONLY INVENTORY

Authority: `research/receipts/2026-08-19-r2-bucket-usage.json`

- 457 objects.
- 22,120,404 bytes.
- 22.120404 MB decimal, about 21.10 MiB binary.
- Inventory operation performed zero writes and zero deletes.

## Binance long-history foundation

### Maximum-available historical coverage discovery — PASS

Authority: `research/receipts/2026-08-18-binance-max-coverage-discovery.json`

- Project history floor: `2018-08`.
- Complete-month edge: `2026-07`.
- 5,760 monthly checks: 4,040 AVAILABLE / 1,720 NO_DATA.
- 1,020 daily checks: 960 AVAILABLE / 60 NO_DATA.
- Coverage boundaries do not themselves authorize materialization, equivalence, Historical Universe membership or source switching.

### Binance staged Trade-Kline expansion plan — PASS / MATERIALIZATION NOT_AUTHORIZED

Authority: `research/receipts/2026-08-18-binance-staged-expansion-plan.json`

Planned order:

- W1 2024: 14 symbols / 168 symbol-months / 504 source archives / 196 future R2 objects.
- W2 2023: 14 symbols / 164 symbol-months / 492 archives / 192 objects.
- W3 2022: 13 symbols / 149 symbol-months / 447 archives / 175 objects.
- W4 2021: 12 symbols / 144 symbol-months / 432 archives / 168 objects.
- W5 2020: 12 symbols / 104 symbol-months / 312 archives / 128 objects.

All waves remain `materialization_authorized=false`. W1 must not proceed while provider-equivalence authority is unresolved for the intended substitution/use case.

## Funding V0.2 — MATERIALIZATION PASS

Storage authority:
`research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json`

Preflight authority:
`research/receipts/2026-08-19-binance-funding-r2-v0-2-full-preflight.json`

Final materialization authority:
`research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json`

Formal result:

- workflow run `32168151926` SUCCESS.
- stage `BINANCE_FUNDING_R2_V0_2_MATERIALIZATION_PASS`.
- 1,003 official source archives.
- 94 annual canonical Parquet objects.
- 94 annual partition receipts.
- 4 run metadata objects.
- 192 / 192 authorized R2 identities post-write verified.
- 91,747 Funding observations.
- 1,138,749 local Parquet bytes in the frozen preflight build.
- 192 uploaded / 0 exact-existing in the final execution.
- HYPEUSDT 2026 remains deferred because its June 2026 source continuity issue was not repaired or interpolated.
- Source switch, provider splicing, Pionex relabeling, Historical Universe membership, backtest admission, trade-plan authorization and live trading remain false.

## Pionex ↔ Binance Equivalence V0.1 — DEFINITIVE FAIL

Protocol: `config/provider_equivalence_v0_1.json`

Frozen result authority:
`research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json`

Result document:
`docs/PIONEX_BINANCE_EQUIVALENCE_V0_1_RESULT.md`

Definitive evidence run: `32206479914`.

- Full source publication was available; this is no longer `PENDING_SOURCE_PUBLICATION`.
- Execution status: PASS.
- Gate status: **FAIL**.
- Frozen overlap: `2026-08-10T08:00:00Z` through `2026-08-17T07:59:59.999Z`.
- 15 symbols / 3 intervals / 45 pairs.
- 18 PASS / 18 REVIEW / 9 FAIL.
- 360 Binance Vision daily archives.
- All 9 FAIL pairs contain `return_direction_agreement_fail`.
- Interval result distribution:
  - `15M`: 4 PASS / 4 REVIEW / 7 FAIL.
  - `60M`: 5 PASS / 8 REVIEW / 2 FAIL.
  - `4H`: 9 PASS / 6 REVIEW / 0 FAIL.
- `source_switch_authorized=false`.
- Hourly source-publication retry was removed because a definitive Gate result now exists.
- The V0.1 result is permanent and must not be rewritten by changing thresholds or scope after evidence.

## Equivalence V0.1 direction forensic — PASS / DESCRIPTIVE ONLY

Authority:
`research/receipts/2026-08-19-pionex-binance-equivalence-v0-1-direction-forensics.json`

Protocol document:
`docs/PIONEX_BINANCE_EQUIVALENCE_V0_1_FORENSICS.md`

Evidence run: `32208040423`.

The forensic replay reloaded the same frozen evidence, reproduced the complete 45-pair `18 PASS / 18 REVIEW / 9 FAIL` result, and then described the exact-sign disagreement shape without re-grading V0.1.

Key findings:

- 623 total direction-mismatch bars across all 45 pairs.
- 432 mismatches are inside the 9 V0.1 FAIL pairs.
- Across all pairs: 539 / 623 mismatches (86.5%) are `ONE_PROVIDER_FLAT`; 84 are opposite non-zero signs.
- In the 9 FAIL pairs: 388 / 432 mismatches (89.8%) are `ONE_PROVIDER_FLAT`; 44 are opposite non-zero signs.
- Mismatches by interval: 536 at `15M`, 78 at `60M`, 9 at `4H`.
- The disagreements are **not** confined to microscopic returns: the FAIL pairs include 16 mismatch bars above 10 bps.
- Therefore a post-hoc tiny-return deadband is not accepted as a legitimate V0.1 fix.
- The forensic evidence supports a measurement-design review, not a source switch.
- R2 forensic access was read-only: zero writes / zero deletes.

V0.1 remains FAIL. The forensic PASS does not authorize W1, backtest admission, Historical Universe membership or live trading.

## Equivalence V0.2 metadata authority transition — TRANSPORT PASS / CAPTURE AUTHORIZED / HOLDOUT UNOPENED

Historical blocker authority remains immutable:
`research/receipts/2026-08-19-provider-equivalence-v0-2-transport-blocked.json`

Self-hosted transport PASS authority:
`research/receipts/2026-08-19-provider-equivalence-v0-2-self-hosted-mac-transport-pass.json`

Replacement metadata capture authority:
`research/receipts/2026-08-19-provider-equivalence-v0-2-forward-metadata-capture-authority-v0-2.json`

Replacement protocol:
`config/provider_equivalence_v0_2_metadata_capture_v0_2.json`

- Hosted GitHub Ubuntu/macOS/Windows HTTP 451 evidence remains preserved.
- Cloudflare Worker HTTP 403 evidence remains preserved.
- Self-hosted macOS ARM64 transport reached the exact Binance USD-M official `exchangeInfo` endpoint with HTTP 200, valid JSON and a valid `symbols[]` array.
- The transport receipt contains sanitized transport evidence only: no increment values, no R2 client, no R2 writes and no holdout candles.
- The old `2026-08-21T00:00:00Z` through `2026-08-27T23:59:59.999Z` candidate remains permanently `SUPERSEDED_UNOPENED_BEFORE_METADATA_CAPTURE_EVIDENCE` and must not be reactivated.
- Replacement holdout is frozen unopened for `2026-08-28T00:00:00Z` through `2026-09-03T23:59:59.999Z`.
- Replacement metadata capture window is `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`, 194 hourly slots, with scheduled attempts at UTC minute 17 and 47.
- Metadata capture is authorized only on `[self-hosted, macOS, ARM64]` and only for the frozen public provider metadata fields.
- The completed transport preflight is not authorized for routine rerun.
- Metadata stability status is `NOT_YET_RUN`.
- Metadata stability PASS, if later achieved, still does **not** authorize holdout candle access; a separate holdout-access authority is required.
- `source_switch_authorized=false`, W1 remains false, backtest admission remains false, automatic trade plan remains false, and live trading remains false.

## Render successor transport line — V0.5 PASS / V0.6 TRANSITION PASS / V0.7 PREPARED

Transport PASS authority:
`research/receipts/2026-08-19-provider-equivalence-v0-5-render-free-transport-pass.json`

Transport transition authority:
`research/receipts/2026-08-19-provider-equivalence-v0-6-render-transport-authority-transition.json`

Prepared successor metadata protocol:
`config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json`

Prepared protocol receipt:
`research/receipts/2026-08-19-provider-equivalence-v0-7-render-metadata-capture-protocol-prepared.json`

- V0.5 Render Free / Frankfurt reached the exact official Binance USD-M `exchangeInfo` endpoint with HTTP 200, valid JSON and a nonempty `symbols[]` array; sanitized evidence recorded `symbol_count=872`.
- V0.6 created a separate versioned transport-authority transition and did not mutate or erase the historical V0.2 Self-Hosted Mac authority.
- V0.7 preserves the exact V0.2 replacement holdout, metadata capture window, 194 hourly slots, UTC `:17/:47` schedule targets, 15-symbol / 45-pair scope and price-increment semantics.
- V0.7 prepares GitHub-hosted Ubuntu orchestration with direct public Pionex metadata transport and Render Free Frankfurt only for the Binance USD-M metadata transport leg.
- The V0.7 Render metadata relay scaffold is hard-disabled in code with `METADATA_RELAY_EXECUTION_AUTHORIZED=false`. Environment variables cannot enable it without a later versioned code/authority change.
- V0.7 has no active schedule trigger, performs no provider metadata capture, authorizes no metadata R2 writes and does not access holdout candles.
- R2 credentials remain GitHub Actions Secrets only and must not be placed in Render.
- FREE-ONLY remains binding: Render stays Free, monthly project runtime budget remains `0 USD`, and the current operational R2 hard stop for this successor design is 8 GB with a required prewrite headroom gate.
- The public Binance `exchangeInfo` path does not require a Binance API key. This is not a project-wide Binance API-key ban; future authenticated Binance scope may be separately versioned. A Binance API key cannot be used as a transport-blocker bypass.
- Until a separate execution/cutover authority is frozen and merged, the V0.2 Self-Hosted Mac path remains the only metadata-capture execution path already authorized by Repository authority.
- Any future V0.7 execution cutover must explicitly prevent the old V0.2 self-hosted scheduled path and the successor Render path from running concurrently.

## Historical Universe — REVIEW PASS / MEMBERSHIP NOT_READY

Authority: `research/receipts/2026-08-18-historical-universe-long-horizon-review.json`

- Long-horizon review prerequisite is satisfied for planned W1 scope: 2024 / 14 symbols / HYPE excluded.
- Formal long-horizon membership is still NOT_READY.
- Future membership requires audited materialized `15M` / `60M` / `4H` partition receipts with actual first/last timestamps and provider-separated provenance.
- No Binance provider evidence may silently create Pionex-native membership.

## Backtest and strategy framework

Existing backtest, Historical Universe framework, historical liquidity, technical-feature, historical SState replay/evidence-ingestion and parameter-sweep components remain implementation-ready from prior merged work.

However:

- framework readiness is not evidence admission;
- Historical Universe membership is not ready;
- Pionex ↔ Binance V0.1 provider equivalence is FAIL;
- metadata stability has not yet been proven;
- the replacement holdout remains unopened and unauthorized for candle access;
- full strategy-signal equivalence remains deferred because required strategy semantics are not yet formally defined;
- no strategy parameter change, automatic trade plan or live execution is authorized.

## Dashboard

Fixed GitHub Pages site:
`https://qookey109-pixel.github.io/crypto-autopilot/`

- Traditional Chinese: `zh-Hant-TW`.
- Repository-authority normalized view only; dashboard JSON itself declares `authority=false`.
- Shows Funding V0.2 materialization PASS, R2 live usage and Equivalence V0.1 FAIL.
- `mode=PAPER-ONLY`.
- `tradePlanAuthorized=false`.
- `liveTradingAuthorized=false`.
- `main` updates affecting dashboard authorities are automatically built and deployed with GitHub Actions.

## Current blockers

1. **V0.7 execution cutover:** successor Render metadata protocol is prepared, but relay enablement, scheduled capture activation and metadata R2 writes remain NOT_AUTHORIZED until a separate versioned cutover authority is frozen.
2. **Old/new capture-path exclusivity:** the future successor path must explicitly prevent concurrent execution with the existing V0.2 self-hosted scheduled capture path.
3. **Metadata stability:** the complete 194-slot stability gate has not run.
4. **Holdout access:** replacement `2026-08-28` through `2026-09-03` holdout is frozen unopened; candle access remains explicitly unauthorized until a separate authority after metadata stability PASS.
5. **Provider substitution/equivalence:** V0.1 is definitive FAIL; Binance must not be substituted for Pionex provenance under that protocol.
6. **Trade-Kline W1:** 2024 materialization remains NOT_AUTHORIZED.
7. **Historical Universe membership:** NOT_READY until audited materialized partitions exist under an authorized path.
8. **Strategy replay admission:** blocked by authority and still-undefined full strategy-equivalence semantics.
9. **HYPE Funding 2026:** remains deferred; no interpolation or provider splice is authorized.
10. **Live execution:** deliberately forbidden; project remains PAPER-ONLY.

## Next formal milestone

### Separate successor Render metadata execution/cutover authority

The next permitted development step is to validate the hard-disabled V0.7 relay and then freeze a separate versioned execution/cutover authority. That authority must exist before any successor Render metadata capture execution or R2 write.

Required discipline:

1. Keep V0.1 permanently FAIL and do not change its thresholds or scope.
2. Preserve the V0.2 Self-Hosted Mac authority, V0.5 Render PASS evidence and V0.6 transition receipt as historical authorities; do not rewrite them.
3. Keep the exact V0.2 replacement holdout and V0.7 inherited metadata window/scope unchanged.
4. Validate only the V0.7 disabled relay behavior while its code execution gate remains false; do not make a Binance metadata relay provider request under V0.7 prepared authority.
5. Before successor execution, freeze a new authority that explicitly disables/resolves the old V0.2 scheduled capture path so both paths cannot capture concurrently.
6. Only that future authority may authorize changing `METADATA_RELAY_EXECUTION_AUTHORIZED` from false and activating a successor schedule.
7. Keep R2 credentials on GitHub Actions only; Render must never receive them.
8. Require a fresh R2 free-tier headroom check before any future metadata write, with the FREE-ONLY 8 GB operational hard stop for this successor design.
9. Require at least one complete valid capture for each of the 194 UTC hourly slots and exact per-provider normalized-vector stability across the full window after execution is separately authorized.
10. Do not fetch or evaluate replacement holdout candles during metadata capture. Metadata stability PASS still requires a separate holdout-access authority before any candle access.
11. Source switch, W1, Historical Universe membership, backtest admission, automatic trade plans and live trading remain blocked.

## Explicitly forbidden next actions

- Do not lower or alter Equivalence V0.1 thresholds.
- Do not shrink the V0.1 15-symbol / 45-pair scope to manufacture PASS.
- Do not reinterpret the V0.1 forensic descriptive bins as Gate thresholds.
- Do not silently add a post-hoc deadband and claim V0.1 PASS.
- Do not re-enable the obsolete hourly source-publication retry.
- Do not reactivate the superseded `2026-08-21` through `2026-08-27` holdout.
- Do not access replacement holdout K-lines before a separate holdout-access authority exists.
- Do not enable the V0.7 Render metadata relay or activate its schedule before a separate execution/cutover authority exists.
- Do not allow V0.2 self-hosted capture and the successor Render capture path to run concurrently.
- Do not give Render R2 credentials.
- Do not use a third-party proxy in place of the exact official Binance endpoint.
- Do not use a Binance API key as a transport-blocker bypass; this restriction does not prohibit separately versioned future authenticated Binance functionality.
- Do not upgrade Render to a paid plan or add a payment method to continue this FREE-ONLY path.
- Do not authorize W1 merely because R2 has ample storage capacity.
- Do not write Binance data into a Pionex-native namespace.
- Do not splice providers or interpolate missing source events.
- Do not change SState frozen core for this historical-data phase.
- Do not authorize automatic trade plans, real-money orders or live trading.
