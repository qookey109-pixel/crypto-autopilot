# Pionex API Baseline — 2026-08-17

This file records the API assumptions used by V0.1. Re-verify official Pionex docs before changing private/live execution code.

## Public futures data used in V0.1

Base URL:

`https://api.pionex.com`

Active perpetual symbols:

`GET /api/v1/common/symbols?type=PERP&status=TRADING`

24-hour futures tickers:

`GET /api/v1/market/tickers?type=PERP`

Best bid/ask futures quotes used by the implementation:

`GET /api/v1/market/bookTickers?type=PERP`

### Runtime documentation discrepancy

On 2026-08-17, a GitHub-hosted live acquisition called the singular route shown on the current Futures market page:

`GET /api/v1/market/bookTicker?type=PERP`

and received HTTP 404. Pionex's current API-key-permissions reference lists both `bookTickers` and `bookTicker`, while the Pionex changelog records `GET /api/v1/market/bookTickers` as the endpoint introduced for best market price/size. The V0.1 client therefore uses plural `bookTickers`, and a regression test freezes that choice. Re-verify if Pionex resolves the documentation discrepancy.

Futures candles:

`GET /api/v1/market/klines`

V0.1 timeframes are supported by the current official documentation:

- `15M`
- `60M`
- `4H`

The documented futures kline request limit is 1–500 records per request. `endTime` is inclusive. Historical backfill therefore pages backward with the next cursor set to `earliest_time - 1 ms`, followed by gap/duplicate/schema validation.

For V0.1 universe selection, the exchange-reported 24h ticker `amount` is used only among USDT perpetual contracts, with best-bid/ask spread as a liquidity sanity gate.

## Deferred private/live API

Pionex currently labels the Futures API as Beta in its official documentation. Private execution is intentionally outside V0.1.

Before any future live milestone, re-verify:

- account Futures API eligibility
- private authentication/signing
- position and order endpoints
- server-side protective stop/TP capabilities
- order/fill private streams
- rate limits
- reconciliation behavior

## Official documentation references

- https://www.pionex.com/docs/api-docs/futures-api/common
- https://www.pionex.com/docs/api-docs/futures-api/market
- https://www.pionex.com/docs/api-docs/references/api-key-permissions
- https://www.pionex.com/docs/api-docs/readme/change-log
- https://www.pionex.com/docs/api-docs/futures-api/general-info/basic-info
