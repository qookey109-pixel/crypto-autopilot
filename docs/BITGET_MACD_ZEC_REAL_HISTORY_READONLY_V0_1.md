# Bitget MACD ZEC Real-History Read-Only V0.1

Status date: 2026-09-18

This experiment applies the already-merged Bitget-style 30m MACD preregistration to the existing governed Binance USD-M Crypto Core 100 history.

## One-shot data scope

- symbol: `ZECUSDT`
- provider provenance: `binance_usdm`
- persistent source: existing Core100 R2 materialization
- source interval: `15m`
- source months: `2022-08` through `2026-07`
- expected governed dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`
- required monthly partitions: 48
- provider fallback: forbidden
- R2 writes: forbidden
- raw candle artifact persistence: forbidden

The runner fails closed if ZEC is absent from the governed Core100 catalog, any monthly partition is missing, any SHA or training-quality check fails, the combined 15m history is not strictly contiguous, or the governed dataset fingerprint differs from the completed training dataset.

## Research method

The execution reuses the frozen V0.1 preregistration:

- 2,304 candidate configurations
- first 70% = development
- 4 chronological development windows
- Top 24 selected from development only
- final 30% = confirmation
- 2 / 5 / 10 bps per-side slippage stress
- confirmation cannot change parameters

The user's original 12/26/9, 3x, 20% margin, 5% stop, 5-bar / 1.2% research filter baseline is also reported separately because it was specified before seeing the real-data results.

## Authority boundary

The one-shot workflow can read only the governed catalog, shard receipts and selected ZEC 15m partitions required to reconstruct the exact completed dataset lineage. The code exposes no R2 write method.

This experiment does not grant formal backtest admission, strategy parameter changes, source switching, replacement holdout access, model promotion, a trade plan, real-money orders, or live trading.
