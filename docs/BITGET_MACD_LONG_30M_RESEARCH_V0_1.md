# Bitget MACD Long 30m Research V0.1

Status date: 2026-09-17

This is a paper-only research harness. It does not change the current strategy, model threshold, quality gate, source authority, holdout state, model promotion state, trade-plan authority, real-money order authority, or live-trading authority.

## User baseline represented

- market: `ZECUSDT`
- direction: LONG only
- source timeframe: local contiguous `15m` OHLCV aggregated deterministically to UTC-aligned `30m`
- MACD: Fast `12`, Slow `26`, Signal `9`
- leverage: `3x`
- margin fraction: `20%`
- stop loss: `5%`
- volatility filter approximation: lookback `5`, minimum fluctuation `1.2%`
- standard Bitget futures taker fee assumption: `6 bps` per side
- default slippage stress assumption: `2 bps` per side

## Important Bitget compatibility boundary

Bitget's public September 2026 documentation confirms manual MACD Fast/Slow/Sig parameters and an advanced volatility-filter setting, but it does not publish the exact formula for the advanced fluctuation filter. Therefore this harness does **not** claim byte-for-byte reproduction of the Bitget bot.

The research approximation is explicitly:

`(highest high - lowest low) / last close`

over the configured number of already-closed 30m bars.

The output always records:

- `bitget_filter_formula_verified=false`
- `fluctuation_filter_semantics=RESEARCH_APPROX_CLOSED_BAR_HIGH_LOW_RANGE_OVER_LAST_CLOSE`

If Bitget later publishes the exact filter formula, replace the approximation in a new version rather than silently changing V0.1 semantics.

## Causality and cost model

- A MACD bullish crossover can only be evaluated after the signal bar closes.
- Entry occurs no earlier than the next 30m bar open.
- A MACD bearish crossover exits no earlier than the next bar open.
- Stop loss is checked intrabar; a gap below the stop exits at the first available open.
- Taker fees and configurable slippage are charged on both entry and exit.
- Funding is supported only when explicit local `FundingPoint` evidence is supplied; it is not fabricated.
- One position is modeled at a time.

## Optimization grid

The default bounded sensitivity grid tests 2,304 configurations across:

- Fast: `8, 10, 12, 14`
- Slow: `21, 26, 30, 35`
- Signal: `5, 7, 9`
- stop: `3%, 4%, 5%, 6%`
- filter: off, `3/0.8%`, `5/1.2%`, `8/1.6%`
- risk profiles:
  - original-style `3x / 20% margin / no additional account-risk cap`
  - `3x / 10% margin / 1% account-risk cap`
  - `2x / 15% margin / 1% account-risk cap`

Candidate ranking is descriptive research only. It prioritizes enough trades, profit factor above 1, return/drawdown, profit factor, return, drawdown, then sample count. It is not a promotion gate and is not evidence of future profitability.

## Execution boundary

The included script accepts a **local JSON candle file only**. It performs:

- no provider requests
- no R2 reads
- no R2 writes
- no holdout access
- no training
- no model promotion
- no source switch
- no trade-plan generation
- no real-money order
- no live trading

A real ZECUSDT historical run must use separately authorized data access / experiment authority. Until then this module is synthetic/local research preparation only.
