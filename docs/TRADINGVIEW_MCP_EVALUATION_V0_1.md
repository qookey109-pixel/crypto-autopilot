# TradingView MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH ONLY / NOT APPROVED FOR RUNTIME**

## Candidate

Registry capability: `tradingview_mcp`

Reviewed upstream:

`atilaahmettaner/tradingview-mcp@a1e54b07e5c21b375363607920f297c5adfbeed4`

Reviewed package version: `0.9.0`.

License: MIT.

## Verified shape

The reviewed repository contains inspectable Python source and tests. Its
documented surfaces include market screeners, technical indicators,
multi-timeframe analysis, Yahoo Finance prices, sentiment/news helpers and a
backtest engine with nine strategies plus walk-forward analysis.

It is an independent project and does not require a TradingView account. Runtime
data is obtained from third-party/public market-data sources through libraries
such as `tradingview-screener`, `tradingview-ta` and Yahoo Finance. News and
sentiment can optionally use a Marketaux API token.

Self-hosting is documented as free. A separate hosted service is paid.

## Useful research surfaces

### Indicator implementation reference

`core/services/indicators_calc.py` contains locally inspectable calculations
for EMA, SMA, RSI, Bollinger Bands, MACD, ATR, Supertrend and Donchian channels.

This is useful as an independent implementation reference when checking formula
semantics. It does not become Crypto Autopilot's canonical indicator authority.

### Screener and multi-timeframe challenger

Exchange screeners and multi-timeframe summaries can be useful for external
cross-checks and discovery research.

The provider layer includes retries, throttling, a short fresh cache and a
stale-while-error fallback. A stale fallback can be useful operationally, but a
future adapter would have to preserve observation/freshness metadata so stale
data cannot be mistaken for current market state.

### Backtest challenger

The reviewed backtest engine is useful as a qualitative challenger because it
includes transaction-cost parameters, mark-to-market drawdown metrics,
trade/equity logs and walk-forward tooling.

It is **not equivalent to Crypto Autopilot's formal validation path**.

Important differences include:

- OHLCV comes from Yahoo Finance rather than the project's canonical
  Binance/Pionex research sources;
- strategies are long-oriented examples rather than the project's strategy
  family contracts;
- commission and slippage are generic fixed percentages;
- exchange-specific funding, margin/liquidation and execution semantics are not
  the project's execution model;
- strategy logic commonly evaluates indicators containing bar `i` and records
  entry/exit at bar `i` close.

That final point requires an explicit market-on-close assumption. Without such
an assumption, using the completed close to decide and fill at that same close
does not satisfy the project's stricter causal/no-lookahead standard. Therefore
the upstream return metrics and rankings are challenger evidence only.

## Interpreted signal boundary

The repository contains threshold-based outputs such as BUY / SELL / HOLD,
ratings, trade setups, strategy rankings and walk-forward labels.

The reviewed `multi_agent_service.py` itself clarifies that its so-called
multi-agent result is a deterministic rule checklist and that its decision is a
threshold artifact rather than a probability.

Crypto Autopilot must not use these upstream labels to:

- select a Strategy Router path;
- rank or promote project strategies;
- alter thresholds;
- admit a portfolio position;
- authorize paper or live execution;
- authorize a real-money order.

## Data-source boundary

This candidate is not a TradingView account/API integration and must not be
treated as a canonical TradingView feed.

Its data can differ from Binance/Pionex by venue, symbol mapping, bar
construction, adjustment rules, timing, cache age and provider availability.

A future runtime comparison would need explicit source, venue, timeframe,
observed-at, available-at and freshness metadata.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Recommended scope:

- indicator-formula implementation reference;
- external technical/screener challenger;
- external backtest methodology challenger;
- no source switch;
- no project strategy ranking or signal authority.

Evaluation receipt:

`research/receipts/2026-09-19-tradingview-mcp-evaluation-v0-1.json`

## Authority

This evaluation grants no installation, external network access, Marketaux
secret use, hosted subscription, MCP runtime, source switch, R2/holdout access,
training, strategy/model promotion, Router/Daily Opportunity integration,
Portfolio Admission authority, order authority or real live trading.
