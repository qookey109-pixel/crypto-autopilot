# Render Free Binance Transport

This directory hosts the zero-cost Render Frankfurt transport runtime used by the provider-equivalence transport line.

Historical lineage is preserved:

- V0.5 proved the diagnostic-only Render Free transport path.
- V0.6 froze a separate transport-authority transition without rewriting V0.2 Self-Hosted Mac authority.
- V0.7 adds a **disabled, fail-closed metadata relay scaffold**. V0.7 does not authorize metadata capture execution, R2 writes or holdout access.

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

Render Free web services may spin down after idle periods. Any future scheduled metadata design must retain freshness and slot fail-closed gates.

## Endpoints

### `GET /health`

Unauthenticated liveness only.

### `GET /check`

Requires `Authorization: Bearer <DIAGNOSTIC_TOKEN>`.

Calls only:

`https://fapi.binance.com/fapi/v1/exchangeInfo`

It returns only sanitized V0.5 transport evidence: upstream status, JSON validity, `symbols[]` validity and symbol count. It does not emit increment values, persist raw exchangeInfo, construct an R2 client, read holdout candles, switch provider or trade.

### `GET /metadata/binance-exchange-info`

V0.7 implementation scaffold only.

The code path is hard-disabled by:

`METADATA_RELAY_EXECUTION_AUTHORIZED = False`

Therefore environment variables cannot activate the relay in V0.7 and no Binance provider request is made through this path. While disabled it returns HTTP 503 with sanitized safety fields only.

A future separately versioned execution/cutover authority must explicitly change the code gate before this endpoint may fetch metadata. That future design is intended to require `METADATA_RELAY_TOKEN` and to forward validated exact upstream exchangeInfo bytes without reserialization, caching or Render-side persistence. R2 credentials must remain on the GitHub Actions side and must not be placed in Render.

Do **not** set or request `METADATA_RELAY_TOKEN` for V0.7; execution is not authorized yet.

## Binance API key boundary

The public Binance USD-M `exchangeInfo` path does not require a Binance API key. That statement applies to this public metadata path only and is **not** a project-wide ban on Binance API keys. Future authenticated Binance functionality may be versioned separately. An API key must not be used as a transport-blocker bypass.

## Render settings

Use exactly:

- Branch: `main`
- Language: `Docker`
- Region: `Frankfurt (EU Central)`
- Root Directory: `infra/render/binance-transport-free`
- Dockerfile Path: `./Dockerfile`
- Instance Type: `Free`
- Health Check Path: `/health`

`DIAGNOSTIC_TOKEN` remains a Render secret for the historical `/check` path. Never commit secret values or paste them into issues/logs.

Do not select a paid instance. Do not add a payment method for this project. If Render suspends the service because free allowance is exhausted, fail closed rather than upgrading.

## Authority boundary

V0.7 does not authorize:

- Render metadata relay enablement;
- scheduled metadata capture;
- metadata R2 writes;
- replacement holdout candle access/evaluation;
- source switching or provider splicing;
- W1 / Historical Universe / backtest admission;
- trade plans, real-money orders or live trading.

Before any V0.7 capture execution, a separate versioned cutover authority must also resolve the old V0.2 self-hosted scheduled path so both transports cannot capture concurrently.
