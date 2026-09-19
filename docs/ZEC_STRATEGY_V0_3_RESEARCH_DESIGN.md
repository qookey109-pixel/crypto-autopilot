# ZEC Strategy V0.3 — Regime-Aware Research Design

Status date: 2026-09-18

## Scope boundary

ZEC V0.3 is an **asset-specific research module only**. It must not become the product's primary architecture, daily default asset, or automatic trade target.

The platform-level objective is multi-asset and opportunity-first:

`governed universe -> daily opportunity selection -> strategy routing -> risk sizing -> execution`

A future ZEC result may contribute evidence to a reusable strategy family, but platform-wide use requires separate multi-asset/generalization validation.

## Motivation

ZEC MACD V0.2 completed successfully as an experiment but failed as strategy evidence. None of the 24 development-selected candidates produced a positive return in the final confirmation window even at the lowest preregistered 2 bps per-side slippage stress.

V0.3 therefore does **not** expand the MACD parameter grid. The research question changes from "which MACD parameters look best?" to:

> Does a 30m MACD trigger show a more robust edge when trades are permitted only inside a causally known bullish 4h trend regime and risk is normalized by ATR?

This is a new structural hypothesis. It is not a continuation of the V0.2 parameter search.

## Existing project capabilities reused

The repository already contains the required deterministic building blocks:

- closed-bar technical features: EMA20/50/200, ATR14, RSI14, MACD, Bollinger and volume features
- point-in-time market regime evidence
- contextual edge analysis
- update/validation separation and stable-neighbor parameter selection
- partition-integrity and holdout guards
- a fail-closed TradingAgents challenger adapter

V0.3 must extend these components instead of replacing them.

## External research sources

Exact source commits and allowed-use boundaries are frozen in:

`research/references/zec-strategy-v0-3-external-sources.json`

The intended contributions are:

**Fincept Terminal** — architecture concepts only. Its separation of data, analytics, backtesting, risk and execution is useful as a research-desk model, but no Fincept code, UI or trade dress is to be copied into this project.

**TradingAgents** — challenger architecture only. The existing project adapter remains research-only. Agent prose may propose or challenge hypotheses before a plan is frozen, but an LLM output cannot become a numeric backtest signal, candidate score, parameter mutation or trade trigger.

**jev-trader** — execution-quality reference only. Spread, depth, imbalance, taker flow, CVD and latency are relevant to a future paper-execution layer. They are not part of V0.3 historical signal research because the currently authorized candle datasets do not contain L2/taker-flow history.

**anti-gambling-trader-tw** — statistical-method reference. V0.3 independently implements a centered-bootstrap research gate and Holm family-wise correction. No upstream code is vendored.

## V0.3 deterministic hypothesis

### Signal timeframe

- source candles: 15m
- decision bars: 30m
- context bars: 4h
- all features become usable only after their source bar closes
- a 30m entry signal is executed no earlier than the next 30m open

### Long entry trigger

The base trigger remains a bullish MACD crossover on a closed 30m bar.

Only two MACD trigger families may be studied:

1. 12 / 26 / 9 — original baseline
2. 12 / 30 / 7 — the least-negative V0.2 selected-confirmation configuration

Including the second configuration does **not** make it validated; V0.2 confirmation has already been seen and is development evidence only for V0.3.

### 4h trend regime

A long entry may be eligible only when the latest causally available 4h technical snapshot satisfies one of two preregistered regime variants:

- `TREND_STRICT`: close > EMA200, EMA20 > EMA50, EMA20 slope/ATR > 0
- `TREND_BASIC`: close > EMA200 and EMA20 > EMA50

No later 4h bar may be attached to an earlier 30m decision.

### Volatility control

V0.3 does not optimize an absolute ZEC volatility threshold. It studies only:

- `ATR_FILTER_OFF`
- `ATR_ROLLING_EXTREME_GUARD`: reject entries when the current 4h ATR14/close is above the causal rolling 90th percentile of the prior 180 closed 4h bars

The current bar must not be included in the percentile reference window.

### Risk and exits

Fixed percentage stop loss is removed from the V0.3 hypothesis.

Candidate stop axes:

- `VOL_STOP_2ATR_BB_HALF`: stop distance = max(2.0 × ATR14, 0.5 × Bollinger Band width)
- `VOL_STOP_2_5ATR_BB_HALF`: stop distance = max(2.5 × ATR14, 0.5 × Bollinger Band width)

The Bollinger component is adaptive: one-half of the full upper-to-lower band width. Stop distance and account-risk sizing are deliberately separate.

There is **no arbitrary percentage cap on stop distance**. If the causal volatility model requires a stop 20%, 30% or more below entry, the research engine preserves that distance rather than tightening it merely to fit a percentage rule.

Candidate account-risk budgets:

- 1.0% of current equity
- 2.5% of current equity
- 5.0% of current equity
- 10.0% of current equity

These values control target loss-at-stop, not stop placement.

Common rules, not sweep axes:

- maximum leverage: 3x
- position size is bounded by both target risk-to-stop distance and leverage/margin limits
- if the 3x leverage ceiling prevents the target risk budget from being reached, the engine must use the smaller feasible position and record both target and realized risk
- a trade must be skipped rather than moved closer to liquidation or given a tighter artificial stop merely to consume the requested risk budget
- bearish MACD crossover exits at the next 30m open
- initial stop may only tighten, never widen after entry
- no averaging down
- no martingale
- no pyramiding
- funding is counted only when explicit point-in-time funding data is supplied; otherwise funding cost is reported as unavailable rather than fabricated

A trailing-stop or time-stop extension is deferred until this simpler structural hypothesis has evidence. Adding them now would increase the research degrees of freedom.

## Candidate family

The frozen structural family is therefore:

- 2 MACD variants
- 2 4h trend variants
- 2 volatility variants
- 2 adaptive ATR/Bollinger stop variants
- 4 account-risk variants

Maximum candidate count: **64**.

This is intentionally far smaller than the V0.2 grid of 2,304.

## Development protocol

The previously viewed ZEC history from 2022-08 through 2026-07 is no longer eligible to act as fresh confirmation data.

For V0.3 it may be used only as development evidence.

Development must:

- use chronological folds
- evaluate the complete 64-candidate matrix
- select exactly one champion before fresh confirmation is accessed
- use robust-first ranking rather than best total return
- require the existing stable-neighbor logic where neighboring candidates exist
- record the full candidate/fold matrix; selective omission is forbidden

TradingAgents or any other LLM may critique the frozen development report, but cannot replace the selected champion.

## Statistical research gate

The new `statistical_edge_gate.py` is research-only.

For the already-selected champion, validation evidence must satisfy at minimum:

- at least 30 realized trades
- positive mean net P&L after configured fees/slippage
- one-sided centered-bootstrap p-value < 0.05
- when a positive development mean exists, validation edge decay no greater than 50%

If several exploratory structural hypotheses are evaluated in the same research family, their p-values must be family-wise controlled with Holm step-down before any claim is made.

The bootstrap assumes trade observations are exchangeable/IID enough for this research approximation. Serial dependence remains a declared limitation; passing this gate is not model promotion or trading authority.

## Fresh confirmation boundary

The V0.2 confirmation period has already been seen and cannot be reused as unseen evidence.

The intended fresh V0.3 confirmation interval is:

`2026-08-01T00:00:00Z <= t < 2026-09-16T00:00:00Z`

This exact interval is recorded **before** any V0.3 fresh-data execution. Data acquisition for it requires a separate explicit read-only authority.

The intended source is public Binance USD-M / Binance Vision ZECUSDT 15m history. Any mixture of monthly/daily archives, gap handling, or publication-lag rules must be preregistered and audited before that data is read.

If the frozen champion produces fewer than 30 realized confirmation trades in this fixed interval, the result is `INSUFFICIENT_EVIDENCE`; the window must not be silently extended after viewing results.

## Transaction-cost confirmation

The frozen champion is evaluated under:

- 2 bps per-side slippage: diagnostic
- 5 bps per-side slippage: primary robustness condition
- 10 bps per-side slippage: adverse stress

Existing 6 bps taker fee per side remains included unless an independently verified execution model replaces it.

A candidate cannot be described as robust if it only survives the 2 bps diagnostic and fails the 5 bps primary condition.

## Future execution-quality layer

The jev-trader-inspired microstructure layer is deliberately deferred from historical V0.3 selection.

A later paper-execution study may add:

- observed spread gate
- L2 imbalance
- 10/25/50 bps depth
- taker-flow/CVD
- maker/post-only fill simulation
- latency and stale-decision accounting

That work needs separately governed microstructure data and does not inherit V0.3 data authority.

## Authority

This design authorizes no new data access and no experiment execution.

It does not authorize strategy promotion, formal holdout access, source switching, model promotion, a formal trade plan, real-money orders or live trading.
