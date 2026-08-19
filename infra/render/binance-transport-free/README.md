# Render Free Binance Transport Diagnostic

This directory is the active **diagnostic-only** zero-cost transport candidate for Provider Equivalence V0.5.

## Frozen deployment shape

- Render Web Service
- Instance type: `Free`
- Region: `Frankfurt (EU Central)`
- Runtime: Docker
- Root Directory: `infra/render/binance-transport-free`
- Dockerfile Path: `./Dockerfile`
- Persistent disk: none
- Monthly project runtime budget: `0 USD`
- Payment method: do not add one for this project

Render Free web services spin down after idle periods and can spin back up on an inbound request. This is acceptable for the diagnostic and future scheduled-capture designs as long as freshness/slot gates remain fail-closed.

## Endpoints

- `GET /health` — unauthenticated liveness only.
- `GET /check` — requires `Authorization: Bearer <DIAGNOSTIC_TOKEN>`.

`/check` calls only:

`https://fapi.binance.com/fapi/v1/exchangeInfo`

It returns only sanitized transport evidence: upstream status, JSON validity, `symbols[]` validity and symbol count. It never emits price increment values, persists raw exchangeInfo, constructs an R2 client, reads holdout candles, switches provider, or trades.

## Render settings

Use exactly:

- Branch: `main`
- Language: `Docker`
- Region: `Frankfurt (EU Central)`
- Root Directory: `infra/render/binance-transport-free`
- Dockerfile Path: `./Dockerfile`
- Instance Type: `Free`
- Health Check Path: `/health`

Set `DIAGNOSTIC_TOKEN` in Render as a secret environment variable. Never commit it to GitHub or paste it into issues/logs.

Do not select a paid instance. Do not add a payment method for this project. If Render suspends the service because a free allowance is exhausted, treat that as fail-closed rather than upgrading.

## Authority

A successful Render transport probe does **not** replace V0.2 Self-Hosted Mac authority. PASS evidence must first be frozen, reviewed, and followed by a separate versioned transport authority transition.
