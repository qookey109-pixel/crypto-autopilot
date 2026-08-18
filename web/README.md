# Qookey Crypto Autopilot Dashboard — D1 Static Shell

This directory contains the first read-only dashboard shell defined by `docs/DASHBOARD_V0_1.md`.

## Local preview

From the repository root:

```bash
python -m http.server 4173 -d web
```

Then open:

```text
http://127.0.0.1:4173/
```

A local HTTP server is required because the dashboard loads `web/data/dashboard.json` with `fetch()`.

## D1 data boundary

`web/data/dashboard.json` is an explicit **safe fixture**. It is not Repository authority and must never be interpreted as one.

D2 will replace the fixture with a server-side normalized authority snapshot API. The browser must never receive:

- Pionex API secrets;
- R2 S3 credentials;
- Cloudflare account credentials;
- unrestricted private R2 access;
- live-order credentials or endpoints.

## D1 views

- Overview
- Data Health
- Signals shell
- Paper Positions shell
- Paper Trades shell
- Performance Center shell
- Backtests shell
- Risk & Gates

## Deployment shape

The `web/` directory is intentionally static and can be served by a static hosting layer such as Cloudflare Pages.

No build step is required for D1.

## Safety

D1 contains no real-money order action, no private exchange endpoint and no live-trading control. `PAPER-ONLY` is visible in the interface and provider provenance remains explicit.
