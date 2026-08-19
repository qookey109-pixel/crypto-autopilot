# Binance USD-M Cloudflare Container Transport Preflight V0.3

This directory contains a diagnostic-only Cloudflare Container probe for the unchanged official Binance USD-M public endpoint:

`https://fapi.binance.com/fapi/v1/exchangeInfo`

## Boundary

This is **not** metadata capture and **not** a provider-equivalence result.

It is allowed to prove only whether a real Cloudflare Container can reach the official Binance endpoint and parse a non-empty `symbols[]` array.

It must not:

- use Binance private API credentials;
- emit price-increment values such as `tickSize`;
- persist raw `exchangeInfo`;
- construct an R2 client or write R2 objects;
- access or evaluate holdout candles;
- switch providers;
- relabel Binance data as Pionex-native data;
- run backtests, generate trade plans, place orders, or enable live trading.

A PASS does not replace the active V0.2 Self-Hosted Mac transport. A separate versioned authority transition is required before any scheduled metadata-capture workflow can change transport.

## Cloudflare requirements

Cloudflare Containers are available on the Workers Paid plan. CI deployment uses a Cloudflare account ID and API token. For Wrangler CI/CD, Cloudflare documents using an account ID plus an API token created from the `Edit Cloudflare Workers` template.

GitHub repository secrets expected by the diagnostic workflow:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`

No Binance API key is required for this probe.

## Network policy

The Container starts with internet access disabled and explicitly allows only:

- `fapi.binance.com`

The Worker endpoint requires a per-run bearer token generated inside GitHub Actions. The token is delivered to Cloudflare as a Worker secret for that deployment and is never committed.

## Validation

Local/static checks:

```bash
python -m pytest tests/test_cloudflare_container_transport_preflight_v0_3.py
cd infra/cloudflare/binance-transport-container
npm install --no-audit --no-fund
npm run typecheck
docker build -t qookey-binance-cloud-transport-v0-3 .
```

The real network probe is intentionally manual via GitHub Actions `workflow_dispatch`. It should be executed only after the scaffold is merged and the two Cloudflare repository secrets are present.
