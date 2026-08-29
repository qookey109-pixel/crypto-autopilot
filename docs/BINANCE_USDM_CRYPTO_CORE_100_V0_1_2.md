# Binance USD-M Crypto Core 100 V0.1.2

Status: **AUTHORIZED AFTER V0.10 WINDOW / NOT STARTED**.

V0.1.2 supersedes Detailed History V0.1.1 before V0.1.1's first eligible
provider request or R2 access. The frozen V0.1 and V0.1.1 configs and receipts
remain immutable historical evidence.

## Materialized scope

- 100 unique USDT-quoted Crypto USD-M markets;
- the original 15 continuity symbols remain mandatory;
- fixed source range `2022-08` through `2026-07`;
- native `15m`, `1h` and `4h` Binance Vision monthly archives;
- all selected markets reach the fixed source-window end;
- 10 serialized, resumable shards of 10 markets;
- R2-only persistent generated data under a dedicated Crypto Core namespace.

Tokenized-stock/ETF candidates and explicit non-Crypto roots are classified
during discovery but excluded before materialization. They require a separate
future dataset, namespace, config, receipt, diagnostics and human review. They
do not consume any of the 100 Crypto slots.

## Execution boundary

The first eligible schedule is `2026-09-04T06:23:00Z` (`14:23 Asia/Taipei`).
Before `2026-09-04T02:00:00Z`, the runner exits before provider or R2 access.
Backfill authority expires at `2026-10-01T00:00:00Z`.

The source ends before the replacement holdout. V0.1.2 does not authorize
holdout candles, source switching, Pionex-native relabeling, Historical
Universe membership, formal backtest admission, model promotion, trade plans,
real-money orders or live trading.

## Expansion rule

Future Crypto or tokenized-equity additions use a new version and append-only
shards. Existing objects must match exactly and may not be silently overwritten.
The broader discovery catalog may remain available as metadata, but catalog
membership is not trading authority.
