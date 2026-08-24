# Binance USD-M Detailed History V0.1.1

Status: **CURRENT / AUTHORIZED AFTER V0.10 WINDOW / NOT YET MATERIALIZED**.

V0.1.1 supersedes the V0.1 execution authority before the first eligible
provider request or R2 access. The V0.1 config and receipt remain unchanged
historical evidence. The only configuration deltas are:

- version `0.1.0` to `0.1.1`;
- a backfill stop exclusive at `2026-10-01T00:00:00Z`.

GitHub cron cannot encode a year. The schedule expression therefore appears
again in later Septembers, but V0.1.1 must exit before provider or R2 access at
and after the stop. The weekly completed-dataset trainer is not a backfill and
may continue after that deadline.

## Preserved V0.1 data contract

- 250 deterministic Binance USD-M USDT markets;
- fixed 2022-08 through 2026-07 source window;
- native `15m`, `1h` and `4h` checksum-backed Binance Vision Klines;
- 25 serialized, resumable 10-market R2 shards;
- original 15 continuity symbols, at least 20 heuristic tokenized-stock/ETF
  candidates, all 19 observed historical-absence candidates and at least 175
  window-end candidates;
- fresh whole-bucket 8 GB headroom gates before provider access and before
  writes, exact existing-object equality and post-write SHA-256 readback;
- R2-only persistent generated history, receipts, models and metrics;
- four chronological walk-forward folds with baseline, fee/slippage,
  drawdown and exposure diagnostics.

The stage stores OHLCV Klines rather than tick-by-tick trade prints. It does
not open the replacement holdout, change V0.10, switch providers, relabel
Binance evidence as Pionex-native, promote models, create trade plans, place
orders or enable live trading.

## Current authority

- config: `config/binance_usdm_detailed_history_v0_1_1.json`;
- receipt:
  `research/receipts/2026-08-24-binance-usdm-detailed-history-v0-1-1-bounded-authority.json`;
- backfill workflow:
  `.github/workflows/binance-usdm-detailed-history-v0-1.yml`;
- weekly trainer:
  `.github/workflows/binance-usdm-detailed-training-v0-1.yml`.

The full unchanged dataset and model design remains documented in
`docs/BINANCE_USDM_DETAILED_HISTORY_V0_1.md`.
