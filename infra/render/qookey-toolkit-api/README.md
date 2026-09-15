# Qookey Crypto Toolkit API Origin V0.1

Status: `PREPARED_RESEARCH_ONLY`.

This directory contains a minimal full-CPython container for the Toolkit REST origin. It intentionally copies only `src/` plus the HTTP entry script and does not install the repository's R2/history dependencies. That keeps this service focused on deterministic, side-effect-free Toolkit functions.

## Required environment

Set a strong secret value in the hosting platform:

```text
QOOKEY_TOOLKIT_API_TOKEN=<secret bearer token>
```

The server refuses a non-loopback bind if this token is absent. Render supplies `PORT`; the image sets `QOOKEY_TOOLKIT_HOST=0.0.0.0`.

Optional:

```text
QOOKEY_TOOLKIT_CORS_ORIGIN=https://your-frontend.example
```

Do not use `*` for CORS on a credentialed public deployment.

## Container build

Build from repository root so the Dockerfile can copy `src/` and `scripts/`:

```bash
docker build -f infra/render/qookey-toolkit-api/Dockerfile -t qookey-toolkit-api .
```

Run locally:

```bash
docker run --rm -p 8788:8788 \
  -e PORT=8788 \
  -e QOOKEY_TOOLKIT_API_TOKEN='replace-me' \
  qookey-toolkit-api
```

Health check:

```bash
curl http://127.0.0.1:8788/healthz
```

Protected route example:

```bash
curl -X POST http://127.0.0.1:8788/v0/risk \
  -H 'Authorization: Bearer replace-me' \
  -H 'Content-Type: application/json' \
  -d '{"equity_usd":10000,"entry_price":100,"stop_price":95}'
```

## Cloudflare pairing

When using `infra/cloudflare/qookey-toolkit-edge`, set the origin's `QOOKEY_TOOLKIT_API_TOKEN` to the same secret stored in the Worker's `ORIGIN_API_TOKEN`. Clients use a separate `EDGE_API_TOKEN` and never need the origin token.

## Safety

This service is not a provider gateway. It does not fetch Binance/Pionex/MAX data, construct an R2 client, access replacement holdout, promote a model, create a formal trade plan, place a real-money order, or enable live trading. Backtest responses remain research evidence only.
