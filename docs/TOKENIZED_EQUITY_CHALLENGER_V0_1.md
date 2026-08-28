# Tokenized Equity Challenger V0.1

## Status

`PREPARED_LOCAL_REPLAY_ONLY`. This challenger is not part of the formal
crypto universe and does not change `SState Intraday Wave V0.1`.

## What is reused

The challenger deliberately reuses the existing crypto candidate scorer:

- multi-timeframe EMA trend
- ADX and directional index
- rolling VWAP distance
- RSI and MACD histogram
- Donchian position
- relative volume and efficiency ratio
- ATR stop/target geometry

## What is different

An instrument enters replay only when its metadata proves all of the following:

- asset class is explicitly `tokenized_stock_candidate`;
- provider is Pionex public futures and status is `TRADING`;
- required closed-candle intervals are present;
- session model is verified;
- a corporate-action policy is recorded;
- observed spread is within the tokenized-equity gate.

The asset class, data coverage, spread, session and corporate-action evidence are
kept in the candidate output. A heuristic label never proves that an instrument
is tradable or historically available.

## Evaluation boundary

- Paper-only, long-side replay in V0.1 because the current crypto baseline is
  long-only. The separate LONG/SHORT challenger remains independent.
- Same fee, slippage, leverage and risk accounting as the crypto baseline.
- Results are reported as tokenized-equity evidence, never as crypto portfolio
  performance.
- No automatic provider reads, schedule, R2 access, model promotion, formal
  trade plan, Pionex Demo automation or live order is authorized.

## Promotion gate

Before any universe expansion, run chronological walk-forward folds with
session-aware sampling, cost/slippage sensitivity, spread stress, corporate
action checks, data-coverage completeness and comparison against the crypto
baseline. A positive sample does not promote the asset class.
