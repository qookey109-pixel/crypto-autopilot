# Project Status

Updated: 2026-08-17

## Project

Qookey Crypto Autopilot

## Repository

`qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1B R2 FOUNDATION READY / PAPER-ONLY**

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

### M1B — Cloudflare R2 foundation

- R2 S3-compatible storage adapter implemented; credentials are secret-manager only.
- Deterministic R2 object-key contract implemented.
- Parquet candle encoding/decoding implemented with Zstandard compression.
- Partition policy established: monthly `15M`; annual `60M` / `4H` by default.
- SHA-256 object receipt and verified download path implemented.
- Real-bucket round-trip proof script added.
- Storage layout is designed for approximately 250 markets and maximum available history capped at eight years.
- Pionex-native histories and future external proxy histories are required to remain provenance-separated.

## M1B not yet authoritative

The Cloudflare R2 bucket has not yet been connected from this environment. M1B must not be marked COMPLETE until a real R2 round-trip proof passes against the project bucket.

Required secret values, never committed:

- `CLOUDFLARE_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

## Not completed

- Real Cloudflare R2 bucket round-trip proof.
- Upload of the bounded M1A dataset to R2.
- Dataset-level R2 manifest/receipt freeze.
- Long-horizon maximum-available historical backfill (target cap: eight years).
- Dynamic historical-universe reconstruction for survivorship-bias-safe backtests.
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

**M1B-PROOF — Real Cloudflare R2 Round Trip**

1. Create/connect the Cloudflare account and R2 bucket for this project.
2. Create an R2 API token / S3 Access Key scoped to the project bucket.
3. Store values only as GitHub/Cloudflare secrets.
4. Run `scripts/r2_roundtrip_proof.py` against the real bucket.
5. Require upload/download SHA-256 equality and row-count equality.
6. Upload the bounded M1A proof dataset and freeze a dataset manifest.
7. Measure actual Parquet compression, then estimate the 8-year / ~250-market storage and API budget.
8. Begin resumable maximum-available historical acquisition only after the proof passes.

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
