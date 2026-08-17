# Project Status

Updated: 2026-08-17

## Project

Qookey Crypto Autopilot

## Repository

`qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1A PIONEX ACQUISITION PROOF COMPLETE / PAPER-ONLY**

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

## Not completed

- Cloudflare R2 bucket/persistence is not connected.
- Parquet partitioning is not implemented.
- Long-horizon historical backfill is not yet materialized.
- Technical indicator calculation (EMA/ATR/volume) is not implemented.
- Real SState output ingestion is not implemented.
- Full event-driven backtest engine is not implemented.
- Fee/funding/slippage model is not implemented.
- Paper position lifecycle and settlement are incomplete.
- Cloudflare Worker/D1/Pages deployment is not configured.
- Pionex private API permission verification is deferred.
- Server-side protective-order verification is deferred.
- Order/position reconciliation and restart recovery are deferred.
- Shadow-live verification is deferred.
- Live trading is forbidden.

## Next milestone

**M1B — Cloudflare R2 Historical Store**

1. Create/connect the Cloudflare account and R2 bucket for this project.
2. Freeze the R2 object-key layout and provenance metadata contract.
3. Add Parquet or equivalently compact partitioned storage for 15M / 60M / 4H candles.
4. Upload a bounded proof dataset and verify round-trip hashes/row counts.
5. Estimate the long-horizon backfill size and API request budget.
6. Only after R2 proof passes, run the larger historical acquisition needed for backtesting.

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
