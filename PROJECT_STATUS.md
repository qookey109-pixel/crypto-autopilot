# Project Status

Updated: 2026-08-18

## Project

Qookey Crypto Autopilot

## Repository

`qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1B COMPLETE / R2 COST BUDGET GATE PASS / BACKTEST CORE V0.1 READY / HISTORICAL UNIVERSE V0.1 READY / TECHNICAL FEATURES V0.1 READY / HISTORICAL SSTATE REPLAY V0.1 READY / HISTORICAL SSTATE EVIDENCE INGESTION V0.1 READY / STRATEGY REPLAY READINESS GATE ACTIVE / PARAMETER SWEEP FRAMEWORK V0.1 READY / HISTORICAL BACKFILL PILOT AUTOMATED / PAPER-ONLY**

No live-money authorization exists.

## Completed

### V0.1 foundation

- Exchange-agnostic adapter boundary established.
- Pionex public futures market-data client established.
- Paper broker scaffolded.
- SState adapter contract established without modifying SState core.
- SState Intraday Wave V0.1 deterministic strategy/risk baseline added.
- CI and secrets hygiene baseline added.

### M1 — Historical Data Foundation

- Active PERP discovery, 24h ticker and best-bid/ask parsing implemented.
- Historical `15M` / `60M` / `4H` backward pagination implemented.
- Inclusive `endTime` handled with `earliest_time - 1 ms` pagination.
- Audits cover duplicates, ordering, gaps, alignment and OHLCV validity.
- Deterministic fixture writer and acquisition CLI tools added.

### M1A — Live Pionex Acquisition Proof

Authoritative receipt: `research/receipts/2026-08-17-m1a-pionex.json`

- Live public acquisition executed from GitHub Actions run `32010845699` at commit `6f6f97ada779e2d2faaf1c4a6c3f82df1354ee9c`.
- Universe is restricted to a versioned crypto-only candidate pool before liquidity ranking.
- Selected 15: BTC, ETH, SOL, HYPE, ADA, BNB, UNI, XRP, LTC, LINK, DOGE, AAVE, AVAX, INJ, SUI.
- Bounded sample: 2026-08-10 08:00 UTC through 2026-08-17 07:59:59.999 UTC.
- 15 symbols x 3 intervals; 13,230 candles total.
- 60 Kline pages plus 3 universe discovery requests.
- Audit PASS: 0 gaps, 0 duplicate timestamps, 0 invalid candles; no silent interpolation.
- Evidence artifact SHA-256: `2cc359fe5248329716e614ae1df4161347c1987a5b34a5b2087a3c97dadab3a4`.
- Bulk extracted JSON was about 2.2 MB for the seven-day proof and was not committed to Git.
- Pionex runtime discrepancy found and frozen: singular `/bookTicker` returned 404; implementation uses plural `/bookTickers` with regression coverage.
- An earlier exploratory run that admitted non-crypto instruments is explicitly non-authoritative.

### M1B — Cloudflare R2 Historical Store

Authoritative completion receipt: `research/receipts/2026-08-18-m1b-r2.json`

- Cloudflare R2 S3-compatible storage adapter is implemented; credentials remain secret-manager only.
- Deterministic R2 object-key contract is implemented.
- Parquet candle encoding/decoding uses Zstandard compression.
- Partition policy remains monthly `15M` and annual `60M` / `4H` by default.
- SHA-256 verified upload/download path is implemented.
- Real Cloudflare R2 round-trip proof passed.
- Frozen M1A bounded dataset materialization passed in GitHub Actions run `32093154424` at head `94145b90c8067e062472be9080635afa879d24ea`.
- Dataset gate: 45 objects, 13,230 rows, 15 symbols, intervals `15M` / `60M` / `4H`.
- Every uploaded Parquet object was downloaded with SHA-256 verification, decoded, and compared for exact candle equality with the frozen source.
- Dataset audit passed with strict timestamp ordering/uniqueness and no silent repair/interpolation.
- Total observed Parquet payload for the seven-day bounded dataset: 425,161 bytes.
- R2 manifest: `manifests/historical/year=2026/month=08/manifest-20260818T024828Z.json`.
- Manifest SHA-256: `e0a8252d0853aeaf2f3fbe87e7c1c48d1450eef40140ee399d2c15bcf7ce8d16`.
- R2 receipt: `receipts/historical/m1b-m1a-upload-32093154424.json`.
- R2 receipt SHA-256: `846ca4d4f668336b277efe7799a5d46077ee080ec7d0c7dbe81b05fc8cc44cd2`.
- Pionex-native histories and any future external proxy histories must remain provenance-separated.

### Historical capacity sizing and backfill design

Primary design document: `docs/HISTORICAL_CAPACITY_AND_BACKFILL_V0_1.md`
Machine-readable estimate: `research/estimates/2026-08-18-historical-capacity.json`

- Capacity sizing is derived from the observed M1B payload, not a guessed compression ratio.
- Conservative linear estimate for 250 markets x 8 years x native `15M` / `60M` / `4H`: approximately 2.956 GB.
- Two-times capacity factor: approximately 5.912 GB; three-times factor: approximately 8.868 GB.
- A `15M`-only comparison is approximately 1.808 GB for 250 markets x 8 years, but native `60M` / `4H` are retained for the first long-history proof because storage is not the limiting factor.
- Full-target partition count upper bound: approximately 28,000 market-data objects under the current monthly `15M` / annual `60M` / annual `4H` policy.
- Strict eight-year / 250-market / three-interval API-page upper design bound is approximately 184,750 Kline requests; actual usage should be lower because provider history differs by market.
- Resumable design freezes deterministic work-item identity, staging before canonical finalize, checkpointed backward pagination, idempotent resume, quarantine-on-mismatch, and historical-universe provenance requirements.

### R2 Cost & Budget Gate V0.1

Authoritative receipt: `research/receipts/2026-08-18-r2-cost-budget.json`
Primary document: `docs/R2_COST_BUDGET_V0_1.md`
Machine-readable estimate: `research/estimates/2026-08-18-r2-cost-budget.json`
Policy: `config/r2_budget_v0_1.json`

- Cloudflare R2 Standard pricing was rechecked against the official pricing documentation on 2026-08-18.
- Current included monthly R2 Standard envelope: 10 GB-month, 1M Class A operations, 10M Class B operations; internet egress is free.
- Planned 250-market x 8-year canonical + retained-staging storage estimate: approximately 5.912 GB-month.
- Planned full-target operation model: approximately 224,000 Class A and 140,000 Class B operations for a fresh successful materialization.
- Planned usage evaluates `PASS` with estimated R2 cost USD 0/month under the frozen pricing snapshot.
- 3x stress: approximately 8.868 GB-month, 672,000 Class A and 420,000 Class B operations; estimated USD 0/month but storage enters `WARN` headroom.
- Project guardrails: storage WARN > 8 GB / BLOCK > 10 GB; Class A WARN > 750k / BLOCK > 1M; Class B WARN > 7.5M / BLOCK > 10M.
- CI executes `python scripts/check_r2_budget.py` and blocks a `BLOCK` result or frozen expectation mismatch.
- PR #13 implementation proof CI run `32098212233` passed unit tests and the R2 cost/budget gate at tested commit `6332f35bfbc32f0cc64488b2f3492f1a5c5a28d6`.
- R2 included usage is account-level; actual account usage must be reviewed before large expansion because unrelated buckets/projects can consume the same allowance.
- This cost gate covers R2 Standard only. Workers, Workflows, Queues, D1 and other Cloudflare services require separate cost gates.

### Historical Backfill Pilot implementation and automation

Initial implementation merge: PR #10 / commit `12baaccd1d29254e15cd87dcbed35ec3c7afc7d5`.
Automation hardening merge: PR #12 / commit `7e8abfa402122bf0424bd47558bad0d3197495e5`.

- R2-backed deterministic checkpoint, staging and per-partition receipt namespaces are implemented.
- Work-item states are `PENDING -> ACQUIRING -> STAGED -> VERIFIED -> FINALIZED`.
- Work identity is provider + market type + symbol + interval + partition.
- Existing finalized work is verified and skipped on rerun.
- A `STAGED` partition can be resumed in a later Python process without refetching its source candles.
- Existing canonical data without matching authority is protected: the pilot refuses to overwrite it.
- Pionex public Kline acquisition is wrapped with a 3 requests/second soft project pace and conservative HTTP 429 backoff.
- The pilot uses the frozen 15-symbol M1A universe, native `15M` / `60M` / `4H`, and a bounded UTC calendar year (default 2025).
- The workflow uses three 5-symbol shards with `max-parallel: 1`.
- Shard 0 includes a planned interruption after a staged partition, followed by a later process that exercises R2-backed resume.
- Each shard has bounded automatic retries while preserving checkpoint state; canonical conflicts and audit failures remain non-retryable safety stops.
- Structured JSON failure diagnostics and run-level aggregate evidence are emitted as GitHub artifacts.
- The workflow supports automatic `main` push triggering, a daily scheduled continuation, and manual dispatch as an override.
- Concurrency prevents overlapping historical pilot runs for the same pilot year.
- PR #10 CI run `32094937866` passed; PR #12 CI run `32097382736` passed.
- No private API, account, position, order or live-trading path was introduced.

### Backtest Engine V0.1 foundation

Primary document: `docs/BACKTEST_ENGINE_V0_1.md`
Implementation merge: PR #14 / commit `b0ad363bb5b6c9bef9db1bc1d8125158d6d01839`.

- Deterministic paper-only LONG execution core is implemented.
- Event evidence follows `StrategySignal -> RiskDecision -> OrderIntent -> Fill -> Position -> PnL` without rewriting SState.
- A strategy signal may fill only on the first candle strictly after the signal timestamp, blocking same-bar lookahead fills.
- If stop and target are both touched by one OHLC candle, V0.1 uses conservative stop-first resolution.
- Existing `RiskConfig` / `size_long_trade` remains the sizing authority, including the 1% risk baseline, leverage cap, daily loss gate and daily trade-count gate.
- Explicit taker fee, adverse slippage and supplied funding-point cost models are implemented.
- Deterministic results include trades, rejected plans, event sequence, equity curve, PnL, drawdown, win rate, profit factor and trade-level Sharpe-style output when defined.
- V0.1 allows one open portfolio position at a time; overlapping signals are rejected instead of silently changing portfolio risk.
- CI run `32102829605` passed all unit/regression tests plus the R2 cost/budget gate.
- No live-order path or private Pionex API was introduced.

### Historical Universe V0.1 foundation

Primary document: `docs/HISTORICAL_UNIVERSE_V0_1.md`
Implementation merge: PR #15 / commit `2cb299d44f75b66c374adf87ce0e83d0ccad4342`.

- Historical membership is evidence-bounded by `provider + market_type + symbol + interval`.
- The index never extrapolates a market before the first authoritative coverage timestamp or after the last authoritative coverage timestamp.
- Default V0.1 eligibility requires native `15M`, `60M` and `4H` coverage at the queried timestamp.
- Native/proxy provenance is explicit and is never inferred from a provider name.
- Verified historical partition receipts can be converted into bounded coverage records; `NO_DATA` does not create membership.
- Overlapping non-identical authority for the same identity is rejected rather than silently reconciled.
- Deterministic snapshots freeze sorted eligible symbols and the authority references used by the query.
- CI run `32102838532` passed all unit/regression tests plus the R2 cost/budget gate.
- Exact listing/delisting discovery, historical liquidity ranking and full 8-year universe reconstruction remain future evidence work.

### Technical Features V0.1 foundation

Primary document: `docs/TECHNICAL_FEATURES_V0_1.md`
Implementation merge: PR #17 / commit `1f40641761e6b78f8a22dfd728187491714268bf`.

- Deterministic raw EMA20, EMA50, EMA20 slope, ATR14, volume SMA20/ratio, previous-high and ATR-normalized EMA20 extension calculations are implemented.
- Feature snapshots are consumable only after `available_at_ms = bar_time_ms + interval_ms`, enforcing closed-bar semantics.
- Existing candle audit is mandatory before calculation; gaps, duplicates, misalignment or invalid OHLCV fail closed with no silent interpolation or repair.
- EMA uses SMA seeding and standard recursive alpha; ATR14 uses Wilder smoothing.
- Future-candle mutation regression tests prove later candles cannot alter earlier technical snapshots.
- The longest baseline warmup is EMA50; normal positive-volume data becomes technically ready at the 50th candle.
- Raw extension is exposed without inventing an overextension threshold.
- Strategy concepts whose numerical/semantic thresholds are not yet frozen remain intentionally absent as booleans.
- CI run `32103247659` passed all unit/regression tests plus the R2 cost/budget gate.

### Historical SState Replay V0.1 foundation

Primary document: `docs/HISTORICAL_SSTATE_REPLAY_V0_1.md`
Implementation merge: PR #18 / commit `826b2626d4f0c4e0c115d8af7aa4a6e48d53019c`.

- Exact-bar, read-only replay authority is implemented for already-recorded SState outputs.
- Each historical point freezes symbol, bar identity, true availability timestamp, unchanged `SStateContext`, source reference and optional SHA-256.
- A point cannot be read before its `available_at_ms` boundary.
- A prior SState value is not implicitly carried forward to an unrecorded bar.
- Conflicting non-identical authority for the same symbol/bar is rejected.
- Stored SState context is returned unchanged; no recomputation, probability reinterpretation or core modification occurs.
- Test fixtures validate the replay contract only and are explicitly not real historical SState evidence.
- CI run `32103390907` passed all unit/regression tests plus the R2 cost/budget gate.

### Historical SState Evidence Ingestion V0.1

Primary document: `docs/HISTORICAL_SSTATE_EVIDENCE_INGESTION_V0_1.md`
Implementation merge: PR #23 / commit `dca0507fa7e160a6dcea25dd552cf05d7dc6b3f0`.

- A deterministic canonical `historical-sstate-records-v0.1` payload schema is implemented.
- Evidence manifests freeze evidence id/status, real-vs-fixture kind, availability basis, interval, producer provenance/SHA-256, source reference, payload SHA-256, record count and generation time.
- V0.1 historical authority admits only `PASS + REAL_RECORDED + RECORDED_RUNTIME` evidence.
- Fixtures are rejected from historical authority even when structurally valid.
- After-the-fact `RECONSTRUCTED` availability is rejected until a separate deterministic reconstruction proof is designed and approved.
- SState evidence must be 4H-aligned and cannot become available before the source 4H bar closes.
- Future-dated manifests, payload SHA mismatch, record-count mismatch, duplicate symbol/bar identities and noncanonical payload encodings fail closed.
- Verified evidence converts into existing `HistoricalSStatePoint` objects without recomputing or modifying SState; payload SHA and evidence id remain in replay provenance.
- CI run `32104898978` passed all unit/regression tests plus the R2 cost/budget gate.
- This is an ingestion contract only; no real historical SState evidence bundle is yet frozen PASS.

### Strategy Replay Readiness V0.1 gate

Primary document: `docs/STRATEGY_REPLAY_READINESS_V0_1.md`
Implementation merge: PR #19 / commit `43535f02ba3120e5c319e3668d6fa431fe668067`.

- Historical replay readiness now distinguishes `PASS`, `FAIL` and `UNDEFINED` instead of silently supplying missing defaults.
- Frozen SState background rules are executable: allowed states, probability availability, >=50 samples and >=0.60 probability.
- Frozen 1H setup rules are executable: EMA20 > EMA50, EMA20 slope > 0 and close > EMA20.
- Incomplete technical warmup fails closed.
- Current authority leaves ATR-normalized overextension, pullback proximity/semantics, reclaim semantics, previous-high break semantics, volume confirmation threshold and structural-stop ATR buffer size `UNDEFINED`.
- `trade_plan_authorized` remains false while mandatory strategy semantics are undefined.
- Backtest Engine V0.1 may simulate explicitly supplied plans, but automatic historical plan generation is not yet authoritative.
- CI run `32103570004` passed all unit/regression tests plus the R2 cost/budget gate.

### Strategy Parameter Freeze / Sweep Framework V0.1

Primary document: `docs/STRATEGY_PARAMETER_SWEEP_V0_1.md`
Machine-readable boundary: `config/strategy_parameter_sweep_v0_1.json`
Implementation merge: PR #21 / commit `69abd931b88950aae50780dc67f3d57d095c2db3`.

- Deterministic numeric/categorical parameter grids and SHA-256 plan fingerprints are implemented.
- Candidate values, UPDATE folds, one disjoint VALIDATION fold, primary metric, trade-count gates, metric floors, drawdown ceilings and local-stability rules must be frozen before evaluation.
- UPDATE selection requires the complete candidate × UPDATE-fold matrix; selective omission is a protocol error.
- Candidate ranking is robust-first using worst-fold primary metric, median primary metric, lower worst drawdown and deterministic id.
- The selected UPDATE candidate must pass a local-neighbor sensitivity/stability gate so an isolated backtest peak cannot be frozen.
- VALIDATION can evaluate only the already-selected UPDATE candidate; validation-time reselection is forbidden.
- PASS and FAIL validation decisions both mark validation consumed; failed validation cannot freeze a parameter set.
- A validated parameter set can be frozen only after PASS with matching plan fingerprints and retains UPDATE evidence digest plus validation provenance.
- Current machine-readable boundary remains `FRAMEWORK_ONLY`: no real candidate values, production sweep thresholds, real validation split or validated parameter set are frozen yet.
- `trade_plan_authorized` therefore remains false.
- Initial PR #21 CI failed only because the new test file imported unavailable `pytest`; tests were converted to the repository's `unittest` harness with no production-code change. Corrected CI run `32104427875` passed all unit/regression tests plus the R2 cost/budget gate.

## Not completed

- Real Historical Backfill Pilot execution evidence against Pionex + Cloudflare R2 is not yet frozen as PASS.
- Real interruption/resume evidence receipt for the one-year pilot.
- Freeze of the one-year pilot dataset/partition authority after all three shards pass.
- Long-horizon maximum-available historical backfill (target cap: eight years).
- Automatic historical-universe source acquisition/reconstruction for survivorship-bias-safe 8-year backtests.
- Historical liquidity reconstruction/ranking for each backtest date.
- Funding-rate history acquisition; the backtest engine currently accepts supplied funding points only.
- Mark-price history.
- Open-interest history.
- Real historical SState evidence production/acquisition and a real evidence bundle passing the ingestion gate with true recorded-runtime availability timestamps.
- Real candidate-space, selection-policy, UPDATE/VALIDATION split freeze and independently validated parameter set for currently `UNDEFINED` strategy rules.
- End-to-end authoritative strategy replay from historical candles + SState into automatically generated Backtest Engine plans.
- Advanced fill simulation such as partial fills/order-book depth and exchange-specific fee tiers.
- Production-grade paper broker position lifecycle, reconciliation and settlement.
- Cloudflare Worker/D1/Pages deployment.
- Cloudflare Workers/Workflows/Queues/D1 cost gate.
- Pionex private API permission verification.
- Server-side protective-order verification.
- Order/position reconciliation and restart recovery.
- Shadow-live verification.
- Live trading is forbidden.

## Next milestone

**Observe and close Historical Backfill Pilot — resumable one-year proof**

1. Let the automated `Historical Backfill Pilot` continue the 2025 run from `main`; manual clicking is no longer required for normal continuation.
2. Require all three 5-symbol shard jobs to complete successfully.
3. Require shard 0 to retain evidence of the planned-stop phase and subsequent R2-backed resume.
4. Require all finalized partitions to pass candle audit, Parquet decode and R2 SHA-256 verification.
5. Confirm no canonical-conflict guard fired and no authoritative M1B object was overwritten.
6. Review each shard evidence artifact and the aggregate pilot evidence.
7. Freeze a Repository authority receipt for the real pilot run.
8. Only after the receipt is reviewed may maximum-available expansion toward the 8-year / approximately 250-market target be authorized.
9. After the one-year pilot closes, prepare a separate Cloudflare Workers/Workflows/Queues/D1 cost gate before CF1 control-plane migration.

### Safe parallel work while the pilot runs

- Prepare the real candidate-space semantics and evidence split for the six `UNDEFINED` strategy rules, but do not consume validation or freeze winning values before the data/split authority is reviewed.
- Design/implement a real SState evidence producer/export workflow against the pinned SState authority; generated records must pass the Historical SState Evidence Ingestion V0.1 gate before replay use.
- Wire historical-universe snapshots into backtest admission once real partition receipts are available.
- Prepare funding-rate/mark-price/open-interest acquisition design without changing Pionex-native Kline authority.
- Do not authorize automatic historical trade plans until missing strategy semantics are versioned and independently validated.
- Do not authorize the 8-year / approximately 250-market expansion until the one-year pilot authority is frozen PASS.

## Safety gates before any live trading

- Backtest quality gates pass.
- Paper trading quality gates pass.
- Shadow-live reconciliation passes.
- Pionex private Futures API access is confirmed for the account.
- Protective stop/TP behavior is verified on the exchange side.
- Idempotent order intent/client IDs exist.
- Restart reconciliation is proven.
- Daily loss / stale-data / API-error kill switches are proven.
- Explicit live authorization is recorded.
