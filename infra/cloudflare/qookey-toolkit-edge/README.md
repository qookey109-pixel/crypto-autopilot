# Qookey Crypto Toolkit Edge V0.2

Status: `PREPARED_RESEARCH_ONLY` / `IMPLEMENTED_NOT_DEPLOYED`.

This Cloudflare Worker is a thin authenticated edge gateway in front of the full-CPython Toolkit V0.2 API origin. It does not contain strategy logic and grants no provider, R2, holdout, promotion, order, or live-trading authority.

## Routes

Public read-only routes:

- `GET /healthz`
- `GET /openapi.json`
- `GET /v0/capabilities`

Protected research routes:

- `POST /v0/validate`
- `POST /v0/indicators`
- `POST /v0/strategy`
- `POST /v0/risk`
- `POST /v0/backtest`
- `POST /v0/stress`
- `POST /v0/compare`
- `POST /v0/report`

The edge accepts a client bearer token (`EDGE_API_TOKEN`) and replaces it with the private origin bearer token (`ORIGIN_API_TOKEN`) before proxying. The client never receives the origin token.

## Required Worker secrets

Set these with Wrangler. Never commit their values:

```bash
cd infra/cloudflare/qookey-toolkit-edge
npx wrangler secret put TOOLKIT_ORIGIN
npx wrangler secret put EDGE_API_TOKEN
npx wrangler secret put ORIGIN_API_TOKEN
```

`TOOLKIT_ORIGIN` must be an HTTPS origin URL with no trailing slash.

If a browser frontend needs cross-origin access, configure exactly one trusted origin:

```bash
npx wrangler secret put CORS_ORIGIN
```

Do not use wildcard CORS for protected routes and do not embed `EDGE_API_TOKEN` in public browser JavaScript. A public frontend should use a server-side backend-for-frontend or Cloudflare Access/authentication.

For local Worker development, `.dev.vars` may be used but must remain untracked.

## Security properties

- Unknown routes and wrong HTTP methods fail closed.
- Protected routes fail closed if edge/origin tokens are absent or invalid.
- Browser preflight requires an exact `CORS_ORIGIN` match.
- Request bodies are capped at 2,000,000 bytes.
- The configured origin must use HTTPS.
- Upstream redirects are blocked.
- `set-cookie` and `location` are stripped from proxied responses.
- Responses are `no-store` and include a request ID plus basic security headers.
- The Worker has no exchange credentials and no direct dataset/holdout bindings.

## Deployment boundary

The code is prepared but deployment/public exposure is not authorized by this repository change. A separate reviewed deployment authority must define the origin URL, secret provisioning, health validation, rollback, and any public-access policy.
