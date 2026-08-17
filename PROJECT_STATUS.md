# Project Status

Updated: 2026-08-17

## Project

Qookey Crypto Autopilot

## Repository

`qookey109-pixel/crypto-autopilot`

## Current formal stage

**V0.1 M1 HISTORICAL DATA FOUNDATION / PAPER-ONLY**

No live-money authorization exists.

## Completed

### V0.1 foundation

- Exchange-agnostic adapter boundary established.
- Pionex public futures market-data client scaffolded.
- Paper broker scaffolded.
- SState adapter contract established without modifying SState core.
- SState Intraday Wave V0.1 scoring gate implemented as a deterministic baseline.
- Risk sizing and daily risk gates implemented.
- Strategy/risk unit tests and CI added.
- Secrets hygiene baseline added.

### M1 implementation

- Active Pionex `PERP` discovery retained as the universe authority input.
- Public 24h futures ticker parser added.
- Public best bid/ask futures parser added.
- Deterministic USDT-PERP universe ranking added: 24h exchange-reported amount desc, spread asc.
- Target universe fixed at 15, with 10–20 as the controlled operating range.
- Historical `15M` / `60M` / `4H` backward pagination implemented.
- Inclusive `endTime` handled with `earliest_time - 1 ms` pagination cursor.
- Historical audit added for duplicates, ordering, gaps, interval alignment and OHLCV validity.
- Deterministic JSON fixture writer added.
- CLI tools added for universe selection and explicit-range backfill.
- M1 unit tests added.

## Not completed

- Live Pionex universe snapshot has not yet been frozen as a research receipt.
- Multi-symbol historical acquisition has not yet been executed for the selected universe.
- Bulk historical persistence to Cloudflare R2 is not connected.
- Parquet partitioning is not implemented.
- Technical indicator calculation (EMA/ATR/volume) is not implemented.
- Real SState output ingestion is not implemented.
- Full event-driven backtest engine is not implemented.
- Fee/funding/slippage model is not implemented.
- Paper position lifecycle and settlement are incomplete.
- Cloudflare Worker/D1/R2 deployment is not configured.
- Pionex private API permission verification is deferred.
- Server-side protective-order verification is deferred.
- Order/position reconciliation and restart recovery are deferred.
- Shadow-live verification is deferred.
- Live trading is forbidden.

## Next milestone

**M1A — Live Pionex Acquisition Receipt**

1. Run the public universe selector against current Pionex data.
2. Freeze the selected 10–20 USDT perpetual symbols and selection inputs as a dated receipt.
3. Acquire a bounded historical sample for all selected symbols at 15M / 60M / 4H.
4. Require audit PASS or explicitly record provider gaps; never interpolate silently.
5. Measure data volume and request count before enabling R2 persistence.
6. Only then establish the R2 bucket/layout and bulk backfill plan.

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
