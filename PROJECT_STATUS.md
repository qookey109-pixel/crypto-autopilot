# Project Status

Updated: 2026-08-18

## Project

Qookey Crypto Autopilot

## Repository

`qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1B COMPLETE / PAPER-ONLY**

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
- Minimum initial R2 write + verified-read operation volume is approximately 28,000 Class A writes plus 28,000 Class B reads, before checkpoint/manifest overhead.
- Current Cloudflare R2 Standard free-tier envelope is sufficient for the candle-only design if the account's free allowance remains available.
- Pionex Kline page limit is 500 and the documented shared IP limit is 10 requests/second; the project soft target is 3 requests/second with conservative 429 backoff.
- Strict eight-year / 250-market / three-interval API-page upper design bound is approximately 184,750 Kline requests; actual usage should be lower because provider history differs by market.
- Resumable design freezes deterministic work-item identity, staging before canonical finalize, checkpointed backward pagination, idempotent resume, quarantine-on-mismatch, and historical-universe provenance requirements.

## Not completed

- Resumable historical backfill pilot implementation and interruption/resume proof.
- Long-horizon maximum-available historical backfill (target cap: eight years).
- Dynamic historical-universe reconstruction for survivorship-bias-safe backtests.
- Funding-rate history.
- Mark-price history.
- Open-interest history.
- Technical indicator calculation (EMA/ATR/volume).
- Real SState output ingestion.
- Full event-driven backtest engine.
- Fee/funding/slippage model.
- Paper position lifecycle and settlement.
- Cloudflare Worker/D1/Pages deployment.
- Pionex private API permission verification.
- Server-side protective-order verification.
- Order/position reconciliation and restart recovery.
- Shadow-live verification.
- Live trading is forbidden.

## Next milestone

**Historical Backfill Pilot — resumable one-year proof**

1. Implement R2-backed work-item checkpoints with states `PENDING -> ACQUIRING -> STAGED -> VERIFIED -> FINALIZED`.
2. Use deterministic identity: provider + market type + symbol + interval + partition.
3. Keep native `15M`, `60M`, `4H` for the pilot.
4. Use the current 15-symbol M1A universe and a bounded one-year acquisition window where provider history exists.
5. Pace Pionex Kline acquisition at a 3 requests/second project soft target; back off at least 65 seconds plus jitter after HTTP 429.
6. Use 5-symbol GitHub Actions shards with `max-parallel: 1` initially.
7. Intentionally interrupt at least one shard and prove restart/resume creates no duplicate or lost candles.
8. Finalize only complete/audited partitions; require SHA-256 R2 verification, Parquet decode, timestamp/gap/OHLCV audit and receipt generation.
9. Freeze pilot evidence before authorizing maximum-available expansion toward the 8-year / approximately 250-market target.

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
