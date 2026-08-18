# Project Status

Updated: 2026-08-18

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

This file is the current project-status index. Detailed evidence remains in the referenced frozen receipts, configs, documents, PRs and workflow artifacts; this summary does not replace those authorities.

## Current formal stage

**V0.1 M1B COMPLETE / R2 COST BUDGET GATE PASS / BINANCE HISTORICAL SOURCE V0.1 READY / BINANCE VISION BULK SOURCE V0.1 READY / BINANCE VISION LIVE PROOF PASS / BINANCE VISION R2 BOUNDED PROOF PASS / BINANCE 2025 COVERAGE SCAN PASS / BINANCE 2025 R2 PILOT PASS / BINANCE OBSERVED R2 BUDGET GATE PASS / BINANCE MAXIMUM-AVAILABLE COVERAGE DISCOVERY PASS / BINANCE FUNDING SOURCE PROOF PASS / BINANCE FUNDING COVERAGE DISCOVERY PASS / BINANCE STAGED MULTI-YEAR EXPANSION PLAN PASS / HISTORICAL UNIVERSE LONG-HORIZON REVIEW PASS / PIONEX-BINANCE EQUIVALENCE GATE PENDING SOURCE PUBLICATION / BACKTEST CORE V0.1 READY / HISTORICAL UNIVERSE V0.1 READY / HISTORICAL UNIVERSE BACKTEST ADMISSION V0.1 READY / HISTORICAL LIQUIDITY RANKING V0.1 READY / HISTORICAL LIQUIDITY BACKTEST ADMISSION V0.1 READY / TECHNICAL FEATURES V0.1 READY / HISTORICAL SSTATE REPLAY V0.1 READY / HISTORICAL SSTATE EVIDENCE INGESTION V0.1 READY / STRATEGY REPLAY READINESS GATE ACTIVE / PARAMETER SWEEP FRAMEWORK V0.1 READY / PIONEX HISTORICAL BACKFILL PILOT AUTOMATED / PAPER-ONLY**

No live-money authorization exists. `trade_plan_authorized=false` remains mandatory.

## Non-negotiable provider and safety boundaries

- **Pionex** is the execution-target exchange and remains authority for frozen Pionex-native evidence.
- **Binance USD-M / Binance Vision** is a provider-separated research-history source and always remains `provider=binance_usdm`.
- Symbol mapping such as `BTC_USDT_PERP <-> BTCUSDT` never converts provenance.
- Binance data must not be written under Pionex-native R2 keys or silently create Pionex-native Historical Universe membership.
- Provider splicing, Pionex-native relabeling and silent interpolation are forbidden.
- Historical target is maximum provider-observed history capped at eight years; uniform eight-year availability is never assumed.
- No staged Trade-Kline wave is authorized for materialization yet.
- Funding coverage PASS is not Funding R2 materialization authority.
- Historical Universe long-horizon review PASS is not Historical Universe membership authority.
- SState frozen core is not modified by these historical-data phases.
- Live trading remains forbidden.

## Frozen data and storage authorities

### Pionex M1 / M1A — PASS

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- Frozen 15-symbol candidate universe: BTC, ETH, SOL, HYPE, ADA, BNB, UNI, XRP, LTC, LINK, DOGE, AAVE, AVAX, INJ, SUI.
- `15M` / `60M` / `4H`: 13,230 candles, zero gaps, zero duplicate timestamps, zero invalid candles.
- Pionex plural `/api/v1/market/bookTickers` runtime behavior is frozen.

### M1B Cloudflare R2 historical store — PASS

Authority: `research/receipts/2026-08-18-m1b-r2.json`

- Real Pionex M1A materialization run `32093154424` PASS.
- 45 objects / 13,230 rows / 425,161 Parquet bytes.
- Zstd Parquet, deterministic keys, SHA-256 upload/download verification and exact candle round-trip equality are frozen.

### R2 Cost & Budget Gate V0.1 — PASS

Authority: `research/receipts/2026-08-18-r2-cost-budget.json`
Policy: `config/r2_budget_v0_1.json`
Estimate: `research/estimates/2026-08-18-r2-cost-budget.json`

- Conservative 250 markets x 8 years canonical reference: about 2.956 GB.
- Canonical + retained staging: about 5.912 GB.
- 3x storage stress: about 8.868 GB.
- Guardrails remain WARN > 8 GB / BLOCK > 10 GB storage; Class A WARN > 750k / BLOCK > 1M; Class B WARN > 7.5M / BLOCK > 10M.

## Binance long-history foundation

### Binance Historical Data Source V0.1 — READY

Document: `docs/BINANCE_HISTORICAL_SOURCE_V0_1.md`
Policy: `config/binance_historical_source_v0_1.json`
Merge: PR #30 / `3cdf7bf36fad17759b423b8a0572c46af738330f`

- Public USD-M Trade Kline, Mark Price, Funding Rate and recent Open Interest adapters are implemented.
- Funding already maps into Backtest `FundingPoint` while retaining Binance provenance.
- OI remains limited to the documented recent provider window and is not treated as long-horizon history.

### Binance Vision Bulk Source V0.1 — READY

Document: `docs/BINANCE_VISION_BULK_SOURCE_V0_1.md`
Policy: `config/binance_vision_v0_1.json`
Merge: PR #31 / `f8e3023337ff27f263297467653c63b129114d2f`

- Official checksum-backed daily/monthly archive ingestion is implemented.
- Source archive revisions fail closed for explicit review.

### Binance Vision Live Proof — PASS

Authority: `research/receipts/2026-08-18-binance-vision-live-proof.json`
Authority merge: PR #34 / `03fbe1ee30c573dbd5d19b78208086c01ebc0636`

- January 2025 BTCUSDT / ETHUSDT / SOLUSDT.
- Six official Trade/Mark archives, 11,160 rows, all checksums and full-month audits PASS.

### Binance Vision -> R2 Bounded Proof — PASS

Authority: `research/receipts/2026-08-18-binance-vision-r2-proof.json`
Implementation: PR #35 / `3e1888ef1aad557a402bd6c5e66c7d80541997b1`
Authority merge: PR #36 / `79a0c90195116e6536896738c7cf9fb7caccfe84`

- BTC/ETH/SOL January 2025 `15M`: 3 objects / 8,928 rows / 251,270 Parquet bytes.
- R2 SHA, decode and exact-candle equality all PASS; Pionex namespace untouched.

### Binance 2025 Coverage Scan — PASS

Authority: `research/receipts/2026-08-18-binance-2025-coverage-scan.json`
Implementation merge: PR #38 / `907deb2ceda11ed70c646c0e2007a0b54a46e728`
Authority merge: PR #39 / `eae72925fc20963926b85e1b21dc9286068d6237`

- 720 checksum-backed checks: 704 AVAILABLE / 16 NO_DATA.
- HYPE 2025 archive presence begins in May; archive presence is not independent listing-date authority.

### Binance 15-market / 2025 R2 Content Pilot — PASS

Authority: `research/receipts/2026-08-18-binance-2025-r2-pilot.json`
Document: `docs/BINANCE_2025_R2_PILOT_V0_1.md`
Implementation merge: PR #40 / `41b80f559b4aa55c40e92a3d94d6912748d5443d`
Authority merge: PR #41 / `ff1b1a978769617523105c4acbcac46267e2fa57`

- 528/528 source archives audited.
- 206 canonical Trade-Kline R2 objects / 671,022 candles / 18,778,928 Parquet bytes.
- 203 new objects uploaded; 3 existing objects exact-verified without overwrite.
- HYPE pre-onset data was not synthesized.

### Observed Binance R2 Budget Gate — PASS

Authority: `research/receipts/2026-08-18-binance-observed-r2-budget.json`
Estimate: `research/estimates/2026-08-18-binance-observed-r2-budget.json`
Implementation: PR #42 / `370a833547d09540d10e6ea633f948d0af0aeddc`
Authority merge: PR #43 / `fcda027598d0d851ccb30c59baa7532974f96808`

- Real 2025 basis: 671,022 rows / 18,778,928 Parquet bytes.
- 250 x 8y observed-capacity canonical projection: about 2.574 GB; retained staging about 5.148 GB; 3x stress about 7.722 GB.
- Existing R2 budget gates remain PASS.

### Maximum-Available Binance Historical Coverage Discovery — PASS

Authority: `research/receipts/2026-08-18-binance-max-coverage-discovery.json`
Protocol: `config/binance_max_coverage_v0_1.json`
Document: `docs/BINANCE_MAX_COVERAGE_DISCOVERY_V0_1.md`
Implementation merge: PR #47 / `02d434178cc6a85f8e83b6cd15a130f8d4b652c1`

- Scanned from project cap floor `2018-08` through complete month `2026-07`, then current-month daily edge.
- 5,760 monthly checks: 4,040 AVAILABLE / 1,720 NO_DATA.
- 1,020 daily checks: 960 AVAILABLE / 60 NO_DATA; latest published edge in that authority execution was `2026-08-16`.
- 180 boundary/current-edge archives audited.
- 15/15 symbols have observed Trade + Mark Price common windows; zero internal monthly archive-presence gaps in observed spans.
- Coverage boundaries are not listing-date, full interior continuity, equivalence or materialization authority.

### Binance Funding Source Proof V0.1 — PASS

Authority: `research/receipts/2026-08-18-binance-funding-source-proof.json`
Protocol: `config/binance_funding_v0_1.json`
Document: `docs/BINANCE_FUNDING_V0_1.md`
Implementation: PR #53 / `4a28f673482c121f44946317ed6d5127ec3917eb`
Authority merge: PR #54 / `f548654f983b2d8159492a6d3003501d88790135`

- Valid proof run `32129522890`, job `95687364367`; CI run `32129522893`, job `95687364093` PASS.
- BTCUSDT / ETHUSDT / SOLUSDT, January 2024: 93 Funding rows each / 279 total.
- Official `.CHECKSUM`, ZIP member, schema, monotonicity, uniqueness and cadence audits PASS.
- Source-declared Funding interval is preserved; the proof scope used 8h intervals.
- Initial exact-millisecond cadence run `32128779729` was superseded before PASS authority. Diagnostic run `32129021753` showed only +/-1..3 ms source `calc_time` jitter, not missing Funding events.
- Source-proof default cadence tolerance is frozen at 10 ms; observed proof maximum was 3 ms. Raw source timestamps are preserved exactly and never rounded/interpolated.
- This authority proves the bounded source path/schema/checksum semantics only; it does not authorize Funding R2 materialization or backtest admission.

### Binance Funding Coverage Discovery V0.1 — PASS / MATERIALIZATION NOT AUTHORIZED

Authority: `research/receipts/2026-08-18-binance-funding-coverage.json`
Protocol: `config/binance_funding_coverage_v0_1.json`
Document: `docs/BINANCE_FUNDING_COVERAGE_V0_1.md`
Implementation: PR #55 / `61704679c00143a074cb5b2ffadb885c311cf922`

- Final proof tree: `25206003464d24b4366bd23faec40934b43c7a6a`; merged implementation `main` tree is identical.
- Final Coverage run `32131873026`, job `95694584611` PASS; same-tree Source Proof `32131873018` PASS; CI `32131873091`, job `95694584508` PASS.
- Auxiliary PR #56 was used only to obtain an independent concurrency group for the exact final tree and was closed without merge.
- Scan window `2018-08` through complete month `2026-07`: 1,440 symbol-month checks / 1,010 AVAILABLE / 430 NO_DATA.
- 15/15 symbols have observed Funding coverage; 30/30 first/last edge archives audited; zero internal monthly archive-presence gaps inside observed spans.
- Funding onset is provider-observed, symbol-specific and not copied from Trade onset. Examples: BTC/ETH `2020-01-01`, INJ `2022-08-16 16:00 UTC`, SUI `2023-05-03 16:00:00.011 UTC`, HYPE `2025-05-30 12:00:00.006 UTC`.
- HYPE's audited current edge uses a source-declared 4h Funding interval; the other audited current edges used 8h in this execution.
- Long-horizon edge diagnostic run `32130801751`, job `95691293211` found maximum source timestamp residual 45 ms across all 30 edges and no missing declared-interval Funding event.
- Coverage edge audit tolerance was therefore re-frozen at 50 ms before Coverage PASS authority; the Source Proof default remains 10 ms. Raw timestamps remain unchanged and residuals beyond the selected authority tolerance fail closed.
- Interior months are checksum-presence evidence only; full interior row-level continuity is not yet proven.
- Funding R2 writes/materialization, source switching, Historical Universe membership and backtest admission remain unauthorized.

### Binance Staged Multi-Year Expansion Plan V0.1 — PASS

Authority: `research/receipts/2026-08-18-binance-staged-expansion-plan.json`
Protocol: `config/binance_staged_expansion_plan_v0_1.json`
Document: `docs/BINANCE_STAGED_MULTIYEAR_EXPANSION_PLAN_V0_1.md`
Implementation merge: PR #49 / `2840be31322e21a2d3fe13060af3f24c2df67af3`

- Trade-Kline-only wave order: `W1=2024`, `W2=2023`, `W3=2022`, `W4=2021`, `W5=2020`.
- Historical increment: 729 symbol-months / 2,187 archives / 859 future R2 objects / 2,793,893 estimated rows / 78,188,670 estimated Parquet bytes.
- Including existing 2025, projected canonical Trade-Kline storage is about 0.09697 GB; 3x stress about 0.29090 GB.
- Incomplete 2026 is deferred.
- Every wave remains `materialization_authorized=false`.

### Historical Universe Long-Horizon Review V0.1 — PASS / MEMBERSHIP NOT READY

Authority: `research/receipts/2026-08-18-historical-universe-long-horizon-review.json`
Protocol: `config/historical_universe_long_horizon_review_v0_1.json`
Document: `docs/HISTORICAL_UNIVERSE_LONG_HORIZON_REVIEW_V0_1.md`
Implementation merge: PR #51 / `e81b1df9db3d085f7bfa237d5126ccdb43786bb4`

- Review prerequisite is satisfied for W1 acquisition scope: 2024 / 14 symbols / 168 symbol-months / HYPE excluded.
- Pre-materialization Historical Universe membership records remain zero.
- Future membership requires audited materialized `15M` / `60M` / `4H` partition receipts with actual first/last timestamps and provider-separated provenance.
- Review PASS does not authorize W1 materialization or backtest admission.

### Pionex <-> Binance Equivalence Gate V0.1 — PENDING SOURCE PUBLICATION

Protocol: `config/provider_equivalence_v0_1.json`
Implementation merge: PR #45 / `1564be073dd878e5116940543f6c3706a94f4a47`
Runner merge: PR #46 / `de5227f065df507f8ed78b4f14ef4a0e0295fb97`

- Frozen before evidence: 15 symbols / Pionex M1A 7-day window / `15M`,`60M`,`4H` / 45 pairs.
- Thresholds, overlap and symbol scope must not be changed after evidence.
- Run `32112849706`: GitHub Azure Binance REST HTTP 451; not a Gate FAIL.
- Run `32113043035`: required `2026-08-17` Binance Vision daily archive unpublished; not a Gate FAIL.
- Run `32113484720`: `execution_status=PENDING_SOURCE_PUBLICATION`, `gate_status=PENDING`, `pair_count=0`, `source_switch_authorized=false`.
- Latest frozen authority therefore remains PENDING SOURCE PUBLICATION. Temporary hourly retry remains active.

## Research and backtest safety layers

### Backtest Engine V0.1 — READY

Document: `docs/BACKTEST_ENGINE_V0_1.md`
Merge: PR #14 / `b0ad363bb5b6c9bef9db1bc1d8125158d6d01839`

- Deterministic LONG-only paper backtest; next-candle fill discipline; conservative stop-first same-bar collision.
- Existing 1% risk baseline, 3x leverage cap, fee/slippage/funding model remain unchanged.

### Historical Universe + Backtest Admission — READY

Documents: `docs/HISTORICAL_UNIVERSE_V0_1.md`, `docs/HISTORICAL_UNIVERSE_BACKTEST_ADMISSION_V0_1.md`
Merges: PR #15 / `2cb299d44f75b66c374adf87ce0e83d0ccad4342`; PR #25 / `213addc9ce55cdd5b606b4c2ee501ff4ce92d05d`

- No evidence, no historical membership.
- Native evidence for all required intervals is mandatory for default admission.
- Proxy/external-provider evidence cannot silently authorize Pionex-native membership.

### Historical Liquidity + Admission — READY / EVIDENCE INCOMPLETE

Documents: `docs/HISTORICAL_LIQUIDITY_V0_1.md`, `docs/HISTORICAL_LIQUIDITY_BACKTEST_ADMISSION_V0_1.md`
Merges: PR #27 / `89a6eb25daf1e5d4559cb1ad6efde49dbb7000f1`; PR #28 / `93f01e8192066145c6f414956d96071b2b9e9f2c`

- Point-in-time ranking/admission contracts are ready.
- Real historical Pionex liquidity evidence series is not yet frozen PASS.

### Technical Features V0.1 — READY

Document: `docs/TECHNICAL_FEATURES_V0_1.md`
Merge: PR #17 / `1f40641761e6b78f8a22dfd728187491714268bf`

- Closed-bar EMA/ATR/volume/previous-high feature calculations are deterministic and anti-lookahead tested.

### Historical SState Replay / Evidence — READY / EVIDENCE INCOMPLETE

Documents: `docs/HISTORICAL_SSTATE_REPLAY_V0_1.md`, `docs/HISTORICAL_SSTATE_EVIDENCE_INGESTION_V0_1.md`
Merges: PR #18 / `826b2626d4f0c4e0c115d8af7aa4a6e48d53019c`; PR #23 / `dca0507fa7e160a6dcea25dd552cf05d7dc6b3f0`

- Exact-bar read-only SState replay/evidence contracts are ready.
- No real historical SState evidence bundle is frozen PASS yet.

### Strategy Replay Readiness + Parameter Sweep — READY / PARAMETERS UNDEFINED

Documents: `docs/STRATEGY_REPLAY_READINESS_V0_1.md`, `docs/STRATEGY_PARAMETER_SWEEP_V0_1.md`
Merges: PR #19 / `43535f02ba3120e5c319e3668d6fa431fe668067`; PR #21 / `69abd931b88950aae50780dc67f3d57d095c2db3`

- Six mandatory semantics remain UNDEFINED: ATR overextension, EMA20 pullback proximity/semantics, EMA20 reclaim, previous-high break, volume confirmation threshold, structural-stop ATR buffer.
- No validated winning parameter set exists.
- `trade_plan_authorized=false` remains mandatory.

## Still not complete

- Pionex one-year Historical Backfill Pilot aggregate evidence is not yet frozen PASS; it remains an execution-target benchmark/equivalence anchor.
- Pionex/Binance Equivalence authority is not frozen PASS.
- W1 Trade-Kline materialization is not authorized; no later staged wave is authorized.
- Historical Universe long-horizon membership remains `NOT_READY` until audited materialized partition receipts exist.
- Binance Funding source proof and maximum observed monthly coverage are frozen PASS, but **Funding R2 materialization is not authorized or frozen PASS**; interior row-level continuity beyond audited edges remains incomplete.
- Binance long-horizon Mark Price materialization is not frozen PASS; only observed coverage boundaries are frozen.
- Real historical Pionex liquidity evidence is not frozen PASS.
- OI beyond the documented recent provider window requires forward accumulation or a separately reviewed source.
- Real historical SState evidence production/acquisition is incomplete.
- Real candidate-space UPDATE/VALIDATION evidence for the six undefined strategy rules is not frozen.
- End-to-end authoritative strategy replay into automatically generated trade plans is not authorized.
- Production-grade paper broker lifecycle/reconciliation/settlement is incomplete.
- Cloudflare Workers/Workflows/Queues/D1 control-plane migration and separate cost gate are incomplete.
- Pionex private execution/protective-order/reconciliation/shadow-live gates are incomplete.
- Live trading is forbidden.

## Next milestone

**Pionex <-> Binance Equivalence Gate V0.1 + W1 explicit staged-expansion authority, with Funding R2 planning in parallel**

1. Keep Equivalence V0.1 thresholds, 15-symbol scope, 45 pairs and overlap unchanged while the latest frozen authority remains `PENDING SOURCE PUBLICATION`.
2. Preserve the temporary retry; source-publication delay is not a Gate FAIL and does not authorize scope changes.
3. When Equivalence produces live evidence, preserve the exact aggregate `PASS` / `REVIEW` / `FAIL` outcome and freeze it separately; only exact PASS may satisfy the W1 prerequisite.
4. Do not claim full strategy-signal equivalence for the six currently UNDEFINED strategy semantics.
5. After Equivalence PASS, create a separate explicit W1-only staged-expansion authority for **2024 / 14 symbols / 168 symbol-months**; do not broaden scope during authorization.
6. Do not execute W1 until its explicit authority is CI-validated and frozen.
7. After future W1 materialization, create audited `15M` / `60M` / `4H` partition receipts and provider-separated Historical Universe records before backtest admission.
8. Funding Source Proof + 15-symbol Funding Coverage are now frozen PASS. Before any Funding R2 writes, quantify the discovered **1,010 available symbol-month** scope against existing R2 storage/operation assumptions.
9. If the Funding scope materially changes the existing cost envelope, freeze a Funding-specific R2 budget review; otherwise freeze a documented no-material-change determination with the calculation basis.
10. Only after the Funding budget decision, create a separate explicit Funding R2 materialization authority naming exact symbols/months/years and verification rules.
11. Funding materialization must remain under `market-data/binance_usdm/...`; it must not create Pionex-native provenance or Historical Universe membership by itself.
12. Mark Price long-horizon materialization remains separate; OI remains recent-window only.
13. Re-run R2 budget/cost gates after any materially larger market count, additional dataset or partition-scheme change.
14. Do not jump directly to 8 years x ~250 markets.
15. Before CF1 control-plane migration, create separate Workers/Workflows/Queues/D1 cost gates.

## Safety gates before live trading

- Backtest quality gates PASS.
- Paper trading quality gates PASS.
- Shadow-live reconciliation PASS.
- Pionex private Futures API permission verified.
- Protective stop/TP behavior verified exchange-side.
- Idempotent order intent/client IDs and restart reconciliation proven.
- Daily-loss / stale-data / API-error kill switches proven.
- Explicit live authorization recorded.
