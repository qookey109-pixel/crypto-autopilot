# Qookey Crypto Toolkit Edge V0.1

Status: `PREPARED_RESEARCH_ONLY`.

This Cloudflare Worker is a thin edge gateway in front of the full-CPython Toolkit API origin. It does not contain strategy logic and it grants no provider, R2, holdout, promotion, order, or live-trading authority.

## Why edge-only

The repository core has full-CPython dependencies and a larger research surface than an edge runtime should own. The Worker therefore handles only routing, client authentication, payload limits, request IDs, CORS, and response hardening. Toolkit calculations remain in the origin service.

## Routes

Public read-only routes:

- `GET /healthz`
- `GET /openapi.json`
- `GET /v0/capabilities`

Protected research routes:

- `POST /v0/indicators`
- `POST /v0/strategy`
- `POST /v0/risk`
- `POST /v0/backtest`

The edge accepts a client bearer token (`EDGE_API_TOKEN`) and replaces it with the private origin bearer token (`ORIGIN_API_TOKEN`) before proxying. The client never needs to know the origin token.

## Required Worker secrets

Set these through Cloudflare/Wrangler. Never commit their values:

```bash
cd infra/cloudflare/qookey-toolkit-edge
npx wrangler secret put TOOLKIT_ORIGIN
npx wrangler secret put EDGE_API_TOKEN
npx wrangler secret put ORIGIN_API_TOKEN
```

`TOOLKIT_ORIGIN` should be the HTTPS base URL of the full-CPython Toolkit API service, with no trailing slash.

If a browser frontend needs cross-origin access, configure exactly one trusted origin:

```bash
npx wrangler secret put CORS_ORIGIN
```

Do not use a wildcard CORS origin for protected routes. Do not embed `EDGE_API_TOKEN` in public browser JavaScript. For a public frontend, use a server-side backend-for-frontend or put Cloudflare Access/authentication in front of the Worker instead.

For local development, `.dev.vars` may be used but must remain untracked.

## Run and deploy

```bash
npx wrangler dev
npx wrangler deploy
```

Do not deploy until the origin API is configured with the same `ORIGIN_API_TOKEN` value and its `/healthz` endpoint passes.

## Security properties

- Unknown routes fail closed.
- Protected POST routes fail closed if edge or origin tokens are absent.
- Browser preflight fails closed unless `CORS_ORIGIN` exactly matches the request origin.
- Request bodies are capped at 2,000,000 bytes.
- `set-cookie` is stripped from origin responses.
- Responses are `no-store` and receive a request ID plus basic security headers.
- The Worker has no exchange credentials and no direct dataset/holdout bindings.

Future Cloudflare Access, native rate limiting, Queues, or Workflows can be layered in front of or beside this gateway without changing Toolkit core contracts.
