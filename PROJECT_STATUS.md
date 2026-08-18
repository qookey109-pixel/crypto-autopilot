# Project Status

Updated: 2026-08-18

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1B COMPLETE / R2 COST BUDGET GATE PASS / BINANCE HISTORICAL SOURCE V0.1 READY / BINANCE VISION BULK SOURCE V0.1 READY / BINANCE VISION LIVE PROOF PASS / BINANCE VISION R2 BOUNDED PROOF PASS / BINANCE 2025 COVERAGE SCAN PASS / BINANCE 2025 R2 PILOT PASS / BINANCE OBSERVED R2 BUDGET GATE PASS / BACKTEST CORE V0.1 READY / HISTORICAL UNIVERSE V0.1 READY / HISTORICAL UNIVERSE BACKTEST ADMISSION V0.1 READY / HISTORICAL LIQUIDITY RANKING V0.1 READY / HISTORICAL LIQUIDITY BACKTEST ADMISSION V0.1 READY / TECHNICAL FEATURES V0.1 READY / HISTORICAL SSTATE REPLAY V0.1 READY / HISTORICAL SSTATE EVIDENCE INGESTION V0.1 READY / STRATEGY REPLAY READINESS GATE ACTIVE / PARAMETER SWEEP FRAMEWORK V0.1 READY / PIONEX HISTORICAL BACKFILL PILOT AUTOMATED / PAPER-ONLY**

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
- Maximum-available Binance historical coverage onset/end discovery for the candidate universe is not yet frozen beyond the 2025 proof.
- Full long-horizon Binance Vision -> R2 expansion is not authorized yet.
- Historical-universe reconstruction for long-horizon backtests is not complete.
- Real point-in-time historical Pionex liquidity evidence is not frozen PASS.
- Binance long-horizon Funding Rate dataset/materialization is not frozen PASS.
- Binance long-horizon Mark Price dataset/materialization is not frozen PASS.
- OI beyond the documented recent provider window requires forward accumulation or a separately reviewed source.
- Real historical SState evidence production/acquisition is not complete.
- Real candidate-space + UPDATE/VALIDATION evidence for the six undefined strategy rules is not frozen.
- End-to-end authoritative historical strategy replay into automatically generated Backtest Engine plans is not authorized.
- Production-grade paper broker lifecycle/reconciliation/settlement is not complete.
- Cloudflare Workers/Workflows/Queues/D1 control-plane migration and its separate cost gate are not complete.
- Pionex private execution permissions/protective orders/reconciliation/shadow-live gates are not complete.
- Live trading is forbidden.

## Next milestone

**Pionex <-> Binance Equivalence Gate V0.1 + maximum-available Binance coverage discovery**

1. Freeze an overlap/equivalence protocol before looking at pass/fail results.
2. Use only mapped symbols with both Pionex-native and Binance-native evidence for the same timestamps; never splice providers.
3. Compare timestamp coverage and OHLC behavior using explicit tolerances; treat exchange-specific volume as venue-specific evidence rather than requiring equality.
4. Compare closed-bar technical features and strategy-relevant rule outcomes where semantics are already frozen.
5. Do not claim full strategy-signal equivalence for the six currently UNDEFINED rules; defer those dimensions until parameters are independently frozen.
6. Produce deterministic per-symbol/per-timeframe PASS/REVIEW/FAIL evidence and an aggregate gate decision.
7. In parallel, scan actual earliest/latest Binance Vision archive coverage for each candidate market instead of assuming 2020 or eight years.
8. Keep the Pionex one-year pilot running/closing as the execution-target benchmark.
9. Build provider-separated Binance Funding and Mark Price historical materialization in parallel; keep OI recent-window only.
10. Re-run observed R2 budget/cost gates after any materially larger source scope or additional dataset is proposed.
11. Only after equivalence + historical coverage/universe review may a staged multi-year expansion be authorized; do not jump directly to 8 years x ~250 markets.
12. Before CF1 control-plane migration, create separate Workers/Workflows/Queues/D1 cost gates.

## Safety gates before live trading

- Backtest quality gates PASS.
- Paper trading quality gates PASS.
- Shadow-live reconciliation PASS.
- Pionex private Futures API permission verified.
- Protective stop/TP behavior verified exchange-side.
- Idempotent order intent/client IDs and restart reconciliation proven.
- Daily-loss / stale-data / API-error kill switches proven.
- Explicit live authorization recorded.
