# Qookey Crypto Toolkit API Origin V0.2

Status: `PREPARED_RESEARCH_ONLY` / `IMPLEMENTED_NOT_DEPLOYED`.

This directory contains a minimal full-CPython container for the Toolkit V0.2 REST origin. It copies only `src/` plus the HTTP entry script and does not install the repository's R2/history cloud dependencies. The service remains focused on deterministic, side-effect-free Toolkit functions.

## Required environment

Set a strong secret in the hosting platform:

```text
QOOKEY_TOOLKIT_API_TOKEN=<secret bearer token>
```

The server refuses a non-loopback bind if this token is absent. Render supplies `PORT`; the image sets `QOOKEY_TOOLKIT_HOST=0.0.0.0`.

Optional browser CORS:

```text
QOOKEY_TOOLKIT_CORS_ORIGIN=https://your-frontend.example
```

CORS is exact-origin only. Do not use a wildcard for a credentialed deployment.

## Build and local check

Build from repository root:

```bash
docker build -f infra/render/qookey-toolkit-api/Dockerfile -t qookey-toolkit-api-v0-2 .
```

Run locally:

```bash
docker run --rm -p 8788:8788 \
  -e PORT=8788 \
  -e QOOKEY_TOOLKIT_API_TOKEN='replace-me' \
  qookey-toolkit-api-v0-2
```

Health check:

```bash
curl http://127.0.0.1:8788/healthz
```

The protected API supports validate, indicators, strategy, risk, backtest, stress, compare, and report under `/v0/*`.

## Cloudflare pairing

When using `infra/cloudflare/qookey-toolkit-edge`, set the origin's `QOOKEY_TOOLKIT_API_TOKEN` to the same secret stored in the Worker's `ORIGIN_API_TOKEN`. Clients use a separate `EDGE_API_TOKEN` and never need the origin token.

## Safety

This service is not a provider gateway. It does not fetch Binance/Pionex/MAX data, construct an R2 client, access replacement holdout, promote a model, create a formal trade plan, place a real-money order, or enable live trading. Backtest/stress/compare/report responses remain research evidence only.

Deployment and public exposure remain unauthorized until a separate reviewed deployment authority explicitly permits them.
