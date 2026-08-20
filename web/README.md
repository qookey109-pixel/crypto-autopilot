# Qookey Crypto Autopilot Dashboard

This directory contains the read-only Traditional Chinese dashboard shell defined by `docs/DASHBOARD_V0_1.md`.

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

## Authority boundary

`web/data/dashboard.json` is a checked-in **safe fixture** for local/static testing. It explicitly declares `authority=false`; it is not a Repository authority and must never be interpreted as one.

The deployed GitHub Pages site is different: CI copies the static shell, rebuilds a normalized snapshot from frozen Repository authorities, then applies the latest authority overlay before deployment:

```text
frozen receipts/configs + workflow topology + PROJECT_STATUS.md
                 |
                 v
scripts/build_dashboard_authority_snapshot.py
                 |
                 v
scripts/apply_dashboard_latest_authority.py
                 |
                 v
_site/data/dashboard.json
```

The generated deployed snapshot also declares `authority=false`. It is a **read-only normalized view** of Repository authority, not a new authority source. If the dashboard conflicts with `PROJECT_STATUS.md` or a frozen receipt/config, the Repository authority wins.

Current generated status includes Funding V0.2 materialization PASS, frozen R2 usage inventory, Equivalence V0.1 definitive FAIL, Render V0.5/V0.6 transport evidence, V0.8 shared-secret PASS, V0.9 authenticated relay-smoke PASS, **V0.10 effective metadata-capture cutover**, metadata stability `NOT_YET_RUN`, replacement holdout `FROZEN_UNOPENED`, and PAPER-ONLY trading boundaries.

V0.10 metadata capture being `AUTHORIZED` on the dashboard means only the frozen public-provider metadata collection path is authorized. It does not mean holdout access, source switching, trade-plan authorization or live trading is authorized.

## Secret and execution boundary

The browser and generated fixture must never receive:

- Pionex or Binance API secrets;
- Render relay token values;
- R2 S3 credentials;
- Cloudflare account credentials;
- unrestricted private R2 access;
- live-order credentials or endpoints.

The dashboard is display-only. It has no authority or control surface to trigger V0.10 capture, change schedules, write R2, open holdout data, switch providers, create trade plans or enable live execution.

## Views

- Overview
- Data Health
- Signals shell
- Paper Positions shell
- Paper Trades shell
- Performance Center shell
- Backtests shell
- Risk & Gates

## Deployment shape

The `web/` directory is intentionally static. GitHub Actions builds the normalized authority view and deploys it to GitHub Pages. No client-side private API or secret-bearing backend is required.

## Safety

The dashboard contains no real-money order action, no private exchange execution endpoint and no live-trading control. `PAPER-ONLY` is visible in the interface and provider provenance remains explicit.
