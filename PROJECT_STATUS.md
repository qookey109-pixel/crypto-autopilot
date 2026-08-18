# Project Status

Updated: 2026-08-18

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1B COMPLETE / R2 COST BUDGET GATE PASS / BINANCE HISTORICAL SOURCE V0.1 READY / BINANCE VISION BULK SOURCE V0.1 READY / BINANCE VISION LIVE PROOF PASS / BINANCE VISION R2 BOUNDED PROOF PASS / BINANCE 2025 COVERAGE SCAN PASS / BINANCE 2025 R2 PILOT PASS / BINANCE OBSERVED R2 BUDGET GATE PASS / BINANCE MAXIMUM-AVAILABLE COVERAGE DISCOVERY PASS / BINANCE STAGED MULTI-YEAR EXPANSION PLAN PASS / PIONEX-BINANCE EQUIVALENCE GATE PENDING SOURCE PUBLICATION / BACKTEST CORE V0.1 READY / HISTORICAL UNIVERSE V0.1 READY / HISTORICAL UNIVERSE BACKTEST ADMISSION V0.1 READY / HISTORICAL LIQUIDITY RANKING V0.1 READY / HISTORICAL LIQUIDITY BACKTEST ADMISSION V0.1 READY / TECHNICAL FEATURES V0.1 READY / HISTORICAL SSTATE REPLAY V0.1 READY / HISTORICAL SSTATE EVIDENCE INGESTION V0.1 READY / STRATEGY REPLAY READINESS GATE ACTIVE / PARAMETER SWEEP FRAMEWORK V0.1 READY / PIONEX HISTORICAL BACKFILL PILOT AUTOMATED / PAPER-ONLY**

No live-money authorization exists. `trade_plan_authorized` remains `false`.

## Provider roles and provenance boundary

- **Pionex** is the execution-target exchange and remains authority for the frozen Pionex-native M1/M1A/M1B evidence.
- **Binance USD-M / Binance Vision** is the preferred candidate source for long-horizon research history.
- Binance data always remains `provider=binance_usdm`; symbol mapping such as `BTC_USDT_PERP <-> BTCUSDT` never converts provenance.
- Binance data must never be stored under Pionex-native R2 keys or silently authorize Pionex-native Historical Universe records.
- A Pionex/Binance overlap + strategy-signal equivalence gate is mandatory before Binance history can substitute for Pionex-native strategy authority.
- Historical target is **maximum provider-available history capped at eight years**, not an assumption that every perpetual market has eight years of data.

## Frozen data/storage authority

### M1 / M1A — Pionex public historical foundation

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- Public Pionex acquisition proof run `32010845699` at `6f6f97ada779e2d2faaf1c4a6c3f82df1354ee9c`.
- Frozen 15-symbol candidate universe: BTC, ETH, SOL, HYPE, ADA, BNB, UNI, XRP, LTC, LINK, DOGE, AAVE, AVAX, INJ, SUI.
- `15M` / `60M` / `4H`, 13,230 candles, 0 gaps, 0 duplicate timestamps, 0 invalid candles.
- Pionex plural `/api/v1/market/bookTickers` runtime behavior is frozen; singular route is not used.

### M1B — Cloudflare R2 historical store

Authority: `research/receipts/2026-08-18-m1b-r2.json`

- Real Pionex M1A materialization run `32093154424` PASS.
- 45 objects / 13,230 rows / 425,161 Parquet bytes.
- Zstd Parquet, deterministic keys, SHA-256 upload/download verification and exact candle round-trip equality are frozen.
- Binance and any external provider must remain in separate R2 namespaces.

### R2 Cost & Budget Gate V0.1

Authority: `research/receipts/2026-08-18-r2-cost-budget.json`
Policy: `config/r2_budget_v0_1.json`
Estimate: `research/estimates/2026-08-18-r2-cost-budget.json`

- Original conservative M1B-derived envelope remains frozen as a reference.
- 250 markets x 8 years canonical estimate: about 2.956 GB.
- Canonical + retained staging: about 5.912 GB.
- 3x storage stress: about 8.868 GB.
- Frozen project guardrails: storage WARN > 8 GB / BLOCK > 10 GB; Class A WARN > 750k / BLOCK > 1M; Class B WARN > 7.5M / BLOCK > 10M.
- CI continues to run `python scripts/check_r2_budget.py`.

## Binance long-history foundation

### Binance Historical Data Source V0.1 — READY

Document: `docs/BINANCE_HISTORICAL_SOURCE_V0_1.md`
Policy: `config/binance_historical_source_v0_1.json`
Merge: PR #30 / `3cdf7bf36fad17759b423b8a0572c46af738330f`

- Public-only USD-M Kline, Mark Price Kline, Funding Rate history and Open Interest history adapters are implemented.
- Trade/Mark historical pagination supports the strategy `15m` / `1h` / `4h` layers.
- Funding can map into Backtest `FundingPoint` while retaining Binance provenance.
- Binance documents OI history as latest one month only; V0.1 conservatively limits OI queries to 30 days and treats longer history as forward-accumulation/separate-source work.

### Binance Vision Bulk Source V0.1 — READY

Document: `docs/BINANCE_VISION_BULK_SOURCE_V0_1.md`
Policy: `config/binance_vision_v0_1.json`
Merge: PR #31 / `f8e3023337ff27f263297467653c63b129114d2f`

- Official daily/monthly USD-M archives are supported for trade Klines and Mark Price Klines.
- Every archive requires official `.CHECKSUM`, exact ZIP SHA-256, expected CSV member, strict timestamp uniqueness/order and no gaps/interpolation.
- Upstream archive SHA changes fail closed for explicit revision review.
- Official helper baseline starts 2020-01-01; individual symbol onset is never assumed.

### Binance Vision Live Proof — PASS

Authority: `research/receipts/2026-08-18-binance-vision-live-proof.json`
Authority merge: PR #34 / `03fbe1ee30c573dbd5d19b78208086c01ebc0636`

- Run `32108454930`, job `95622625128`, CI `32108454911` PASS.
- January 2025 BTCUSDT / ETHUSDT / SOLUSDT.
- 3 monthly `15m` trade-Kline + 3 monthly `1h` Mark Price archives.
- 6/6 official CHECKSUM PASS; 11,160 rows; full-month coverage PASS.

### Binance Vision -> R2 Bounded Proof — PASS

Authority: `research/receipts/2026-08-18-binance-vision-r2-proof.json`
Implementation: PR #35 / `3e1888ef1aad557a402bd6c5e66c7d80541997b1`
Authority merge: PR #36 / `79a0c90195116e6536896738c7cf9fb7caccfe84`

- Run `32109048193`, job `95624370904`, CI `32109048136` PASS.
- BTC/ETH/SOL January 2025 `15M`: 3 objects / 8,928 rows / 251,270 Parquet bytes.
- Every source SHA, R2 SHA, Parquet decode and exact-candle equality check passed.
- Only `market-data/binance_usdm/...` was touched; Pionex canonical namespace remained untouched.

### Binance 2025 Coverage Scan — PASS

Authority: `research/receipts/2026-08-18-binance-2025-coverage-scan.json`
Implementation merge: PR #38 / `907deb2ceda11ed70c646c0e2007a0b54a46e728`
Authority merge: PR #39 / `eae72925fc20963926b85e1b21dc9286068d6237`

- Run `32109845513`, job `95626701407`, CI `32109845422` PASS.
- 15 candidates x 12 months x (`15m`,`1h`,`4h` trade + `1h` Mark) = 720 checksum-backed checks.
- 704 AVAILABLE / 16 NO_DATA.
- 14/15 symbols have all 12 months of scanned 2025 archive presence.
- HYPEUSDT has archive presence only from 2025-05 through 2025-12; January-April are explicit NO_DATA for all four scanned archive types.
- Archive presence is not listing-date or content-completeness authority by itself.

### Binance 15-market / 2025 R2 Content Pilot — PASS

Authority: `research/receipts/2026-08-18-binance-2025-r2-pilot.json`
Document: `docs/BINANCE_2025_R2_PILOT_V0_1.md`
Implementation merge: PR #40 / `41b80f559b4aa55c40e92a3d94d6912748d5443d`
Authority merge: PR #41 / `ff1b1a978769617523105c4acbcac46267e2fa57`

- Pilot run `32110538170`, job `95628773842`, CI `32110538110` PASS.
- 528/528 source archives passed official checksum + candle audit.
- 206 R2 canonical trade-Kline objects: 176 monthly `15M`, 15 annual `60M`, 15 annual `4H`.
- 671,022 candles / 18,778,928 Parquet bytes.
- 203 new objects uploaded; 3 prior BTC/ETH/SOL January objects were exact-verified and not overwritten.
- All annual cross-month audits, R2 SHA verification, Parquet decode and exact-candle equality checks passed.
- HYPEUSDT first observed audited 2025 Klines: `15M` 2025-05-30 10:30 UTC; `60M` 10:00 UTC; `4H` 08:00 UTC. These are observed Kline onsets, not independent listing-date authority.
- No synthetic HYPE January-April/early-May data was created.

### Observed Binance R2 Budget Gate — PASS

Authority: `research/receipts/2026-08-18-binance-observed-r2-budget.json`
Estimate: `research/estimates/2026-08-18-binance-observed-r2-budget.json`
Implementation: PR #42 / `370a833547d09540d10e6ea633f948d0af0aeddc`
Authority merge: PR #43 / `fcda027598d0d851ccb30c59baa7532974f96808`

- Basis: real 2025 Binance pilot, 671,022 rows / 18,778,928 Parquet bytes.
- Partial-HYPE missing rows are conservatively imputed before scaling so partial availability cannot lower the target estimate.
- 250 markets x 8 years canonical: about **2.574 GB**.
- Canonical + retained staging: about **5.148 GB**.
- 3x capacity stress: about **7.722 GB**.
- Planned operations retain the conservative 224k Class A / 140k Class B envelope; 3x stress 672k / 420k.
- Planned and 3x stress both evaluate PASS under the frozen R2 guardrails, with estimated R2 cost USD 0/month under the frozen pricing snapshot, subject to account-shared free-tier usage.
- CI runs both the original M1B budget gate and `python scripts/check_binance_observed_r2_budget.py`.

### Maximum-Available Binance Historical Coverage Discovery V0.1 — PASS

Authority: `research/receipts/2026-08-18-binance-max-coverage-discovery.json`
Protocol: `config/binance_max_coverage_v0_1.json`
Document: `docs/BINANCE_MAX_COVERAGE_DISCOVERY_V0_1.md`
Implementation merge: PR #47 / `02d434178cc6a85f8e83b6cd15a130f8d4b652c1`

- Run `32120274866`, job `95658986018`, CI `32120274739` PASS.
- Discovery assumed no provider onset month and scanned from the project eight-year cap floor `2018-08` through complete month `2026-07`, then daily archives through `2026-08-17`.
- 5,760 monthly checks: 4,040 AVAILABLE / 1,720 NO_DATA.
- 1,020 current-month daily checks: 960 AVAILABLE / 60 NO_DATA.
- All 60 NO_DATA daily checks are exactly `2026-08-17` across 15 symbols x four frozen series; `2026-08-16` is the latest published daily edge in this authority execution.
- 180 first/last/current-edge archives were checksum/content audited.
- 15/15 symbols have a Trade common window and a Trade + Mark Price common window; no symbol has an internal monthly archive-presence gap within its observed span.
- Common observed onsets are symbol-specific: BTC/ETH begin 2020-01-01; HYPE begins 2025-05-30; INJ begins 2022-08-17; SUI begins 2023-05-03; all exact 15-symbol timestamps are frozen in the authority receipt.
- The workflow-tested merge-ref tree and merged `main` tree are identical: `b42fc54d629185ccbd9fbca1865239dd52c37613`.
- This authority freezes coverage boundaries only. It does not prove listing dates, full interior content continuity, Pionex/Binance equivalence, source-switch authority, large-scale R2 backfill authority or live-trading authority.

### Binance Staged Multi-Year Expansion Plan V0.1 — PASS

Authority: `research/receipts/2026-08-18-binance-staged-expansion-plan.json`
Protocol: `config/binance_staged_expansion_plan_v0_1.json`
Document: `docs/BINANCE_STAGED_MULTIYEAR_EXPANSION_PLAN_V0_1.md`
Implementation merge: PR #49 / `2840be31322e21a2d3fe13060af3f24c2df67af3`

- Valid planning run `32122690358`, job `95666394952`, CI `32122690359` PASS.
- The first planner execution `32122498652` failed before producing a plan because it read the frozen 2025 authority counters from the wrong schema level; the parser/tests were corrected to the formal nested `scope` schema before the PASS run. No R2 writes occurred.
- Planning is Trade-Kline only and derives scope from frozen observed coverage; 2025 is excluded because it is already materialized PASS, while incomplete 2026 is explicitly deferred.
- Frozen wave order: `W1=2024`, `W2=2023`, `W3=2022`, `W4=2021`, `W5=2020`.
- Historical increment: 729 symbol-months / 2,187 source archives / 859 future R2 objects / 2,793,893 estimated rows / 78,188,670 estimated Parquet bytes.
- Including existing 2025, projected canonical Trade-Kline storage is about **0.09697 GB**; canonical + retained staging about **0.19394 GB**; 3x capacity stress about **0.29090 GB**.
- Deferred 2026 through July: 15 symbols / 105 symbol-months / 402,413 estimated rows / 11,261,755 estimated bytes; no 2026 materialization is authorized by this plan.
- The workflow-tested merge-ref tree and merged implementation `main` tree are identical: `dd462c8322f5df9c0ecdb2ff54397636dce9bee4`.
- Every wave has `materialization_authorized=false`. W1 is not authorized until Equivalence PASS authority, Historical Universe long-horizon review and an explicit staged-expansion authority all exist.
- Mark Price, Funding, historical liquidity and historical SState remain separate future authorities; this plan does not authorize source switching, Pionex-native relabeling, 8y x ~250 expansion or live trading.

### Pionex <-> Binance Equivalence Gate V0.1 — PENDING SOURCE PUBLICATION

Protocol: `config/provider_equivalence_v0_1.json`
Implementation merge: PR #45 / `1564be073dd878e5116940543f6c3706a94f4a47`
Runner merge: PR #46 / `de5227f065df507f8ed78b4f14ef4a0e0295fb97`

- Protocol was frozen before live evidence: 15 symbols, frozen Pionex M1A 7-day window, `15M` / `60M` / `4H`, 45 pairs.
- Thresholds must not be changed after seeing evidence; overlap must not be shortened and symbols must not be removed to obtain a result.
- Cross-venue volume equality is intentionally excluded; provider splicing remains forbidden.
- Full strategy equivalence is deferred for the six mandatory strategy semantics that remain UNDEFINED.
- Run `32112849706` failed before a Gate result because Binance REST returned HTTP 451 from the GitHub Azure runner; this is not a Gate FAIL.
- Run `32113043035` produced no Gate result because the required Binance Vision `2026-08-17` daily archive was not yet published; this is not a Gate FAIL.
- Run `32113484720` completed with `execution_status=PENDING_SOURCE_PUBLICATION`, `gate_status=PENDING`, `pair_count=0`, `source_switch_authorized=false`.
- Maximum-available coverage run `32120274866` independently reconfirmed that all 60 frozen symbol/series daily checks for `2026-08-17` were still `NO_DATA` at execution time.
- Temporary hourly retry remains active. `source_switch_authorized=false` remains frozen until a separately versioned authority explicitly changes it.

## Research/backtest safety layers — READY

### Backtest Engine V0.1

Document: `docs/BACKTEST_ENGINE_V0_1.md`
Merge: PR #14 / `b0ad363bb5b6c9bef9db1bc1d8125158d6d01839`

- Deterministic LONG-only paper backtest core.
- Signal fills no earlier than the next candle; same-bar stop/target collision defaults conservative stop-first.
- Existing risk authority remains 1% risk baseline, 3x leverage cap, daily -3R and max daily new-trade gate.
- Fee, adverse slippage and supplied funding costs are modeled.

### Historical Universe + admission

Documents: `docs/HISTORICAL_UNIVERSE_V0_1.md`, `docs/HISTORICAL_UNIVERSE_BACKTEST_ADMISSION_V0_1.md`
Merges: PR #15 / `2cb299d44f75b66c374adf87ce0e83d0ccad4342`; PR #25 / `213addc9ce55cdd5b606b4c2ee501ff4ce92d05d`

- Historical market membership is evidence-bounded; no current-universe backprojection.
- Backtest plans must be historically eligible at their own signal timestamps.
- Proxy/provider data cannot silently authorize Pionex-native membership.

### Historical Liquidity + admission

Documents: `docs/HISTORICAL_LIQUIDITY_V0_1.md`, `docs/HISTORICAL_LIQUIDITY_BACKTEST_ADMISSION_V0_1.md`
Merges: PR #27 / `89a6eb25daf1e5d4559cb1ad6efde49dbb7000f1`; PR #28 / `93f01e8192066145c6f414956d96071b2b9e9f2c`

- Point-in-time liquidity ranking and admission contracts are READY.
- Missing/stale/incomplete liquidity evidence fails closed rather than becoming a strategy loss.
- Real historical Pionex liquidity evidence series is not yet frozen PASS.

### Technical Features V0.1

Document: `docs/TECHNICAL_FEATURES_V0_1.md`
Merge: PR #17 / `1f40641761e6b78f8a22dfd728187491714268bf`

- Closed-bar EMA20/EMA50/EMA20 slope/ATR14/volume ratio/previous-high/ATR-normalized extension are deterministic and anti-lookahead tested.
- No undefined strategy threshold is silently invented.

### Historical SState replay/evidence

Documents: `docs/HISTORICAL_SSTATE_REPLAY_V0_1.md`, `docs/HISTORICAL_SSTATE_EVIDENCE_INGESTION_V0_1.md`
Merges: PR #18 / `826b2626d4f0c4e0c115d8af7aa4a6e48d53019c`; PR #23 / `dca0507fa7e160a6dcea25dd552cf05d7dc6b3f0`

- Exact-bar read-only SState replay and evidence-ingestion contracts are READY.
- Only real recorded-runtime evidence can become historical SState authority.
- No real historical SState evidence bundle is yet frozen PASS.

### Strategy Replay Readiness + Parameter Sweep

Documents: `docs/STRATEGY_REPLAY_READINESS_V0_1.md`, `docs/STRATEGY_PARAMETER_SWEEP_V0_1.md`
Merges: PR #19 / `43535f02ba3120e5c319e3668d6fa431fe668067`; PR #21 / `69abd931b88950aae50780dc67f3d57d095c2db3`

- Replay readiness distinguishes PASS / FAIL / UNDEFINED.
- Six mandatory semantics remain UNDEFINED: ATR overextension, EMA20 pullback proximity/semantics, EMA20 reclaim, previous-high break, volume confirmation threshold, structural-stop ATR buffer.
- Parameter sweep framework freezes UPDATE selection / sensitivity / one-shot disjoint VALIDATION rules, but no real candidate space or validated winning parameter set exists yet.
- `trade_plan_authorized=false` remains mandatory.

## Still not complete

- Pionex one-year Historical Backfill Pilot aggregate evidence is not yet frozen PASS; it remains the execution-target benchmark/equivalence anchor.
- Pionex/Binance candle/feature/strategy-signal equivalence authority is not yet frozen.
- Staged multi-year Trade-Kline planning is frozen PASS, but **no wave materialization is authorized**; full long-horizon Binance Vision -> R2 expansion remains incomplete.
- Historical-universe reconstruction/review for long-horizon backtests is not complete.
- Real point-in-time historical Pionex liquidity evidence is not frozen PASS.
- Binance long-horizon Funding Rate dataset/materialization is not frozen PASS.
- Binance long-horizon Mark Price dataset/materialization is not frozen PASS; only maximum-available Mark Price coverage boundaries are now frozen PASS.
- OI beyond the documented recent provider window requires forward accumulation or a separately reviewed source.
- Real historical SState evidence production/acquisition is not complete.
- Real candidate-space + UPDATE/VALIDATION evidence for the six undefined strategy rules is not frozen.
- End-to-end authoritative historical strategy replay into automatically generated Backtest Engine plans is not authorized.
- Production-grade paper broker lifecycle/reconciliation/settlement is not complete.
- Cloudflare Workers/Workflows/Queues/D1 control-plane migration and its separate cost gate are not complete.
- Pionex private execution permissions/protective orders/reconciliation/shadow-live gates are not complete.
- Live trading is forbidden.

## Next milestone

**Pionex <-> Binance Equivalence Gate V0.1 + Historical Universe long-horizon review**

1. Keep the frozen Equivalence V0.1 protocol unchanged while the required Binance Vision `2026-08-17` source remains unpublished according to the latest frozen authority.
2. Preserve the temporary hourly retry; source-publication delay is not a Gate FAIL and does not authorize threshold/scope changes.
3. When live execution reaches `execution_status=PASS`, read all 45 pair evidence and preserve the exact aggregate `PASS` / `REVIEW` / `FAIL` outcome.
4. Do not claim full strategy-signal equivalence for the six currently UNDEFINED rules; defer those dimensions until parameters are independently frozen.
5. If an Equivalence Gate outcome is produced, freeze it in a separate authority receipt without changing thresholds after evidence; only an exact PASS outcome may be frozen as PASS.
6. Remove the temporary hourly schedule only after an Equivalence authority is frozen.
7. Use `research/receipts/2026-08-18-binance-staged-expansion-plan.json` as the frozen planning authority for the current 15-symbol Trade-Kline expansion; do not regenerate waves by assuming uniform onset dates.
8. Perform the Historical Universe long-horizon review before any W1 materialization. Existing current-universe membership must not be backprojected into earlier years without point-in-time evidence.
9. Keep every staged wave unauthorized until all three frozen prerequisites exist: Equivalence PASS authority, Historical Universe long-horizon review, and explicit staged-expansion authority naming the exact wave/scope.
10. Build provider-separated Binance Funding historical materialization in parallel; Mark Price materialization may use the frozen coverage boundaries, while OI remains recent-window only.
11. Re-run observed R2 budget/cost gates after any materially larger market count, additional dataset or changed partition scheme is proposed.
12. Do not jump directly to 8 years x ~250 markets, and do not start W1 merely because its projected capacity is small.
13. Before CF1 control-plane migration, create separate Workers/Workflows/Queues/D1 cost gates.

## Safety gates before live trading

- Backtest quality gates PASS.
- Paper trading quality gates PASS.
- Shadow-live reconciliation PASS.
- Pionex private Futures API permission verified.
- Protective stop/TP behavior verified exchange-side.
- Idempotent order intent/client IDs and restart reconciliation proven.
- Daily-loss / stale-data / API-error kill switches proven.
- Explicit live authorization recorded.
