# Pionex API Baseline — 2026-08-17

This file records the API assumptions used by V0.1. Re-verify official Pionex docs before changing private/live execution code.

## Public futures data used in V0.1

Base URL:

`https://api.pionex.com`

Active perpetual symbols:

`GET /api/v1/common/symbols?type=PERP&status=TRADING`

Futures candles:

`GET /api/v1/market/klines`

V0.1 timeframes are supported by the current official documentation:

- `15M`
- `60M`
- `4H`

The documented futures kline request limit is 1–500 records per request. Historical backfill therefore requires deterministic pagination via `endTime` plus gap/duplicate validation.

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
- https://www.pionex.com/docs/api-docs/futures-api/general-info/basic-info
