# Project Status

Updated: 2026-08-17

## Project

Qookey Crypto Autopilot

## Repository target

`qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 FOUNDATION / PAPER-ONLY**

No live-money authorization exists.

## Completed in bootstrap

- Exchange-agnostic adapter boundary established.
- Pionex public futures market-data client scaffolded.
- Paper broker scaffolded.
- SState adapter contract established without modifying SState core.
- SState Intraday Wave V0.1 scoring gate implemented as a deterministic baseline.
- Risk sizing and daily risk gates implemented.
- Strategy/risk unit tests added.
- CI workflow added.
- Secrets hygiene baseline added.

## Not completed

- Historical backfill pagination and R2 persistence.
- Universe ranking from liquidity/volume/spread.
- Technical indicator calculation (EMA/ATR/volume).
- Real SState output ingestion.
- Full event-driven backtest engine.
- Fee/funding/slippage model.
- Paper position lifecycle and settlement.
- Cloudflare Worker/D1/R2 deployment.
- Pionex private API permission verification.
- Server-side protective-order verification.
- Order/position reconciliation and restart recovery.
- Shadow-live verification.
- Live trading.

## Next milestone

**M1 — Pionex Historical Data Foundation**

1. Discover active PERP symbols.
2. Rank/select a controlled 10–20 symbol universe.
3. Backfill 15M / 60M / 4H candles with provenance.
4. Validate ordering, duplicates, gaps and candle schema.
5. Store deterministic local fixtures first; R2 integration follows.

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
