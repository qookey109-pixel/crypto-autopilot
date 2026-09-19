# Crypto Market Data MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH ONLY / NOT APPROVED FOR RUNTIME**

## Candidate

Registry capability:

`crypto_market_data_mcp`

Reviewed upstream:

`eliasfire617/crypto-market-data-mcp@7720d7116e26e578037c519d6fdae0d9ba0e8a75`

License: MIT.

## What was verified

At the reviewed commit, the MCP server exposes 13 documented tools across six
configured exchanges: Bybit, Binance, OKX, Hyperliquid, Gate and KuCoin.

The reviewed source uses CCXT public market-data surfaces for:

- price / ticker;
- order book;
- OHLCV;
- recent trades;
- current and historical funding;
- open interest;
- Binance global long/short account ratio;
- limited liquidation history;
- cross-exchange funding comparison.

The exchange factory does not configure exchange API keys. Repository searches
performed during this evaluation found no `create_order`, `cancel_order`,
`fetch_balance` or `withdraw` path.

That evidence applies only to the pinned commit. A future upstream update must
be reviewed again before its pin can change.

## Best fit for Crypto Autopilot

The strongest incremental value is not another EMA/MACD implementation and not
another canonical OHLCV source.

The useful additions are derivatives context:

```text
funding rate + funding interval
open interest amount/value
Binance long/short account ratio
        ↓
prefetched derivatives context
        ↓
future regime / strategy research
```

These fields complement the existing technical layer and External Market Context
V0.1.

## Important semantic boundaries

### Funding comparison

The upstream `compare_funding` helper annualizes rates and emits an
`arb_spread` summary.

Crypto Autopilot may use the underlying funding observations as research
evidence, but the upstream "arbitrage" framing is not a trading instruction.

Any future internal record must preserve at least:

- venue;
- symbol;
- raw funding rate;
- funding interval;
- observed timestamp;
- available timestamp.

### Open interest

Open interest is a derivatives-positioning context feature. Missing venue
support must fail closed; it must not be silently substituted with another
provider.

### Long/short ratio

The reviewed implementation is specifically Binance USD-M global long/short
account ratio. It is not a cross-exchange universal positioning statistic.

The internal context must therefore preserve:

- provider = Binance;
- period;
- long/short ratio;
- long percentage;
- short percentage;
- causal timestamp.

## Duplicative surfaces

Price, OHLCV, order book and recent trades overlap existing project data paths.

They may later be useful for diagnostics or cross-provider comparison, but this
evaluation does not create a second canonical market-data authority.

Liquidations are also available only on a limited capability-dependent basis.
The project already has dedicated liquidation candidates, so this source should
remain a challenger/cross-check for that field.

## Runtime observations

The upstream server includes useful operational patterns:

- bounded retries;
- exponential backoff;
- request and overall timeouts;
- per-exchange concurrency bounds;
- TTL caching;
- structured errors;
- capability checks.

Those are design references only.

HTTP mode also includes bearer-key authentication, quota tiers and an optional
gateway-trust bypass. Crypto Autopilot does not need those billing/server
features and this evaluation grants no credential or gateway-bypass authority.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Recommended next step:

Build an internal, no-network, prefetched derivatives-context contract covering:

- funding;
- open interest;
- Binance long/short ratio.

Use synthetic or existing non-holdout fixtures first. Do not change Strategy
Router, Daily Opportunity scoring, provider authority or trading behavior.

Evaluation receipt:

`research/receipts/2026-09-19-crypto-market-data-mcp-evaluation-v0-1.json`

## Authority

This evaluation grants no:

- automatic schedule;
- code import;
- runtime dependency;
- MCP runtime;
- external-network/provider access;
- hosted API key;
- gateway-auth bypass;
- adapter execution;
- Strategy Router integration;
- Daily Opportunity integration;
- R2 access;
- holdout access;
- source switch;
- training;
- model promotion;
- formal backtest admission;
- trade-plan authority;
- real-money order authority;
- real live trading.
