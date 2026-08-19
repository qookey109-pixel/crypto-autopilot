# Koyeb Free Binance Transport Diagnostic

This directory is a **diagnostic-only** zero-cost transport candidate for Provider Equivalence V0.4.

## Frozen deployment shape

- Koyeb Web Service
- Instance type: `free`
- Region: `fra` (Frankfurt)
- Builder: Dockerfile
- Port: `8080`
- Persistent volume: none
- Monthly runtime budget: `0 USD`

Koyeb documents one Free Instance per organization. The Free Instance can run in Frankfurt or Washington D.C. and scales to zero after one hour without traffic.

## Endpoints

- `GET /health` — unauthenticated liveness only.
- `GET /check` — requires `Authorization: Bearer <DIAGNOSTIC_TOKEN>`.

`/check` calls only:

`https://fapi.binance.com/fapi/v1/exchangeInfo`

It returns only sanitized transport evidence: upstream status, JSON validity, `symbols[]` validity and symbol count. It never emits price increment values, persists raw exchangeInfo, constructs an R2 client, reads holdout candles, switches provider, or trades.

## One-time external setup

A future real proof requires a Koyeb account and one Free Web Service. The project should use GitHub-driven deployment so pushes to the selected branch are automatically rebuilt and deployed.

Do not select Nano/Eco/paid instance types. Do not upgrade the organization plan for this project.

The runtime secret `DIAGNOSTIC_TOKEN` must be stored in Koyeb as an environment variable and must never be committed to GitHub.

## Authority

A successful transport probe does **not** replace V0.2 Self-Hosted Mac authority. PASS evidence must first be frozen, reviewed, and followed by a separate versioned transport authority transition.
