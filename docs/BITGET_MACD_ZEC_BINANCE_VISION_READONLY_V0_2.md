# Bitget MACD ZEC Public Binance Vision Read-Only V0.2

Status date: 2026-09-18

V0.2 is the prepared fallback after V0.1 failed closed because ZECUSDT is not a member of the governed Core100 catalog. V0.1 authority is consumed and is not reusable.

## Frozen public source

- provider: Binance USD-M public data
- delivery: Binance Vision monthly `klines`
- symbol: `ZECUSDT`
- interval: `15m`
- source months: `2022-08` through `2026-07`
- archive count: exactly 48
- one ZIP plus its official `.CHECKSUM` per month
- R2 access: none
- provider fallback: none
- raw candle persistence: none

Each archive must pass the existing Binance Vision checksum parser and strict kline audit. The 48 archives must then form one strictly contiguous 15-minute series from 2022-08-01 00:00 UTC through 2026-07-31 23:45 UTC.

## Research method is unchanged

The merged preregistration remains binding:

- 2,304 candidates
- 70% development
- 4 chronological development windows
- Top 24 selected on development only
- final 30% confirmation
- 2 / 5 / 10 bps per-side slippage stress
- confirmation cannot change parameters

The original user baseline remains separately reported.

## Execution boundary

This preparation grants no V0.2 data-access authority. The workflow starts only when the separate V0.2 one-shot authority receipt is created.

No formal project holdout, strategy mutation, source switch, model promotion, trade plan, real-money order, or live trading is authorized.
