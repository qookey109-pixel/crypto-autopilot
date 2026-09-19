# ZECUSDT MACD Validation V0.2 — Preserved Evidence

Status date: 2026-09-18

This document preserves the outcome of the completed ZECUSDT Bitget-style MACD research without carrying forward any consumed one-shot execution authority or trigger workflow.

## V0.1

The first attempt failed closed because `ZECUSDT` was not present in the governed Crypto Core 100 catalog.

No ZEC historical partition was read, no candidate grid was started, and no provider request or R2 write was performed.

Run: `35297163219`

## V0.2

The second attempt used public Binance Vision monthly USD-M `ZECUSDT` 15m archives from 2022-08 through 2026-07.

Execution evidence:

- workflow run: `35298599786`
- trigger head: `251206ba3d32c327abe09d225f7e256ddebc46c7`
- workflow conclusion: `success`
- artifact id: `10528883728`
- artifact digest: `sha256:207d186881c8a637f2047162b53d3a620bee2202da8a15798cf82b7bb9c3b50b`
- report SHA-256: `3ad232da5a11392d42872c9b47477bc3517e925deac504197f92f70c3d2c8306`
- source rows: `140256`
- monthly archives: `48`
- provider requests: `96`
- R2 access: no
- raw candle persistence: no
- formal project holdout access: no

## Preregistered result

The frozen validation method evaluated 2,304 candidates on 70% development data, selected Top 24 using development-only evidence, then evaluated them on the final 30% confirmation window under 2 / 5 / 10 bps per-side slippage stress.

Positive-return confirmation candidates:

- 2 bps: `0 / 24`
- 5 bps: `0 / 24`
- 10 bps: `0 / 24`

Therefore the preserved interpretation is:

`EXECUTION PASS / STRATEGY EVIDENCE REJECT`

The original 12/26/9 baseline returned -81.2794% over the full source period. Its confirmation return was +0.8936% at 2 bps, -23.9088% at 5 bps, and -53.1040% at 10 bps.

## Governance boundary

This preservation does not authorize:

- rerunning V0.1 or V0.2
- new provider or R2 reads
- strategy changes
- formal backtest admission
- replacement holdout access
- source switching
- training or model promotion
- formal trade plans
- real-money orders
- live trading

The consumed authority receipts and one-shot trigger workflows are intentionally **not** preserved into this clean evidence branch.
