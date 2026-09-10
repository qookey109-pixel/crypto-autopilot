# Pionex Funding History V0.1

## Purpose

Prepare the missing historical-funding input for the fixed Pionex V0.2
`BTC_USDT_PERP` capacity sample without using Binance funding as a substitute
and without requiring a private Pionex account API.

Pionex's current Futures Market API documents the public
`GET /api/v1/market/fundingRates` endpoint for historical funding rates. The
request accepts a perpetual `symbol`, optional millisecond `endTime`, and a
`limit` from 1 through 500. This protocol uses that provider-native public
source only.

This stage is **prepared, not execution authority**. It performs no provider
request, R2 read/write, holdout access, backtest admission, trade plan or live
trade.

## Exact target

- Provider: `pionex_public_futures`
- Symbol: `BTC_USDT_PERP`
- Window: `2026-08-01T00:00:00Z` inclusive through
  `2026-08-28T00:00:00Z` exclusive
- Endpoint: `https://api.pionex.com/api/v1/market/fundingRates`
- Authentication: none/public
- Page limit: 500
- Maximum requests: 3
- Retry count: 0

The first request sets `endTime` to the exclusive right boundary minus one
millisecond. If the oldest returned funding timestamp is still newer than the
left boundary, the next request uses `oldest_funding_time - 1ms`. Pagination
continues only until the returned data reaches or crosses the left boundary.

The collector fails closed if the bounded request budget is exhausted before
that proof exists.

## Completeness rules

Funding cadence is deliberately **not** hard-coded. A provider may change
funding intervals, so the protocol does not invent missing 4h/8h events and
does not zero-fill a presumed cadence.

Every returned observation must:

- match `BTC_USDT_PERP`;
- have a finite funding rate;
- have a non-negative, unique provider timestamp;
- be at or before the request cursor;
- preserve the provider's own timestamp and rate.

Duplicate timestamps fail instead of being deduplicated. Provider errors fail
without retry. An empty page before the left boundary is proven also fails.

Only observations inside the half-open target window are emitted after the
collector has proven that pagination reached the left boundary.

## Relation to Simulation Readiness V0.3

The Pionex V0.2 K-line PASS supplies 15M/60M/4H prices but no historical
funding series. Simulation Readiness V0.3 therefore keeps
`full_simulation_ready=false`.

This funding protocol is designed to resolve that one cost-input blocker.
Success in a future separately authorized funding acquisition would still not
be a model-quality PASS or profitability claim. Production V0.2 R2 data
admission and the final funding-to-backtest integration remain separately
reviewed steps.

Config SHA-256: `9117e707203b35ef9d7420b96033cd339b97c549f03e3cdae2ecece4637b6834`.

## Authority

Only synthetic/offline fixture validation is allowed by this prepared stage.
No production Pionex request, R2 access, holdout access, training, formal
backtest admission, strategy mutation, source switch, trade plan, real-money
order or live trading is authorized.
