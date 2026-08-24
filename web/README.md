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

V0.11 metadata-stability evaluator rules are already **PREPARED / FROZEN BEFORE PRODUCTION EVIDENCE**, but production R2 evaluation is still unauthorized. Therefore the dashboard must continue to show metadata stability as `NOT_YET_RUN`; evaluator readiness is not a stability result.

V0.10 metadata capture being `AUTHORIZED` on the dashboard means only the frozen public-provider metadata collection path is authorized. It does not mean holdout access, source switching, trade-plan authorization or live trading is authorized.

## Secret and execution boundary

The browser and generated fixture must never receive:

- Pionex or Binance API secrets;
- Render relay token values;
- R2 S3 credentials;
- Cloudflare account credentials;
- unrestricted private R2 access;
- live-order credentials or endpoints.

The dashboard is display-only. It has no authority or control surface to trigger V0.10 capture, run V0.11 production evaluation, change schedules, write R2, open holdout data, switch providers, create trade plans or enable live execution.

The paper-training workflow may replace `data/paper-training.json` in the Pages
artifact with its latest bounded public-data replay. The browser only renders
candidate signals, simulated trades and aggregate metrics. It cannot contact
Pionex, submit Demo orders or mutate Repository state.

Persistent generated historical datasets are kept online in the authorized R2
namespaces; GitHub Actions runner files are disposable and removed after
verified publication. Raw training history is not copied into the dashboard and
must remain provider-separated from Pionex evidence.

## Interface direction

The V0.5 visual shell follows a Mintlify-inspired documentation-product rhythm:
a white canvas, universal Inter typography, one Mint Green functional accent,
square 4px controls, restrained 16px cards and a full-bleed teal hero. A
floating research-product mockup bridges the hero and the austere evidence
sections below it.

The original generated cloud-garden artwork at
`web/assets/cloud-garden-v4.jpg` is decorative only and has no authority or
model-input role. Earlier dashboard assets are retained as historical design
material but are no longer rendered by the current shell.

The overview deliberately summarizes the evidence pipeline and critical gates;
the remaining eight views preserve the complete read-only inspection surface.
The research calendar is sourced from Repository state and
`docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md`, but remains a normalized roadmap
view rather than execution authority.

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
