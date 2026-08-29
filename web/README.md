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

CI also rebuilds the non-authoritative research calendar from the current
versioned Repository sources before publishing:

```text
V0.10 cutover + Crypto Core 100 V0.1.2 + prepared Paper successor
       + Strategy Research Loop / Edge configs
       + continuous-learning roadmap + SState evidence boundary
                 |
                 v
scripts/build_research_calendar_projection.py
                 |
                 v
_site/data/research-calendar.json
```

The Strategy view is rebuilt from the six current Repository strategy and
analysis configs rather than from copied or hard-coded UI values:

```text
baseline + technical + shadow + research loop + edge + parameter sweep
                 |
                 v
scripts/build_strategy_projection.py
                 |
                 v
_site/data/strategy.json
```

Both generated projections contain an explicit UTC generation time. The UI
converts only that supplied value to Asia/Taipei. It never substitutes the
browser load time when the source timestamp is missing. Paper observation time
comes only from `paper-training.json.observedAtUtc`; a missing value remains
visibly unavailable.

The generated deployed snapshot also declares `authority=false`. It is a **read-only normalized view** of Repository authority, not a new authority source. If the dashboard conflicts with `PROJECT_STATUS.md` or a frozen receipt/config, the Repository authority wins.

Current generated status includes Funding V0.2 materialization PASS, frozen R2 usage inventory, Equivalence V0.1 definitive FAIL, Render V0.5/V0.6 transport evidence, V0.8 shared-secret PASS, V0.9 authenticated relay-smoke PASS, **V0.10 effective metadata-capture cutover**, the current Strategy Research Loop / Edge Validation `PREPARED_RESEARCH_ONLY` state, metadata stability `NOT_YET_RUN`, replacement holdout `FROZEN_UNOPENED`, and PAPER-ONLY trading boundaries.

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
`web/assets/images/cloud-garden-v4.jpg` is decorative only and has no authority
or model-input role. The three unused predecessor images were removed from the
current tree during V0.1 project convergence; Git history retains them.

The overview deliberately summarizes the evidence pipeline and critical gates;
the remaining eight views preserve the complete read-only inspection surface.
The research calendar is rendered from the safe, non-authoritative
`web/data/research-calendar.json` projection. That file records its Repository
lineage, exact Asia/Taipei windows and safety boundary. Client-side time logic
may label a stage as upcoming, in progress or past its window, but it never
infers that evidence passed. `docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md` remains
the roadmap source and Repository authorities still win every conflict.

The Strategy view also explains SState in plain language. It distinguishes the
4H market-context gate from a trade signal or per-trade win probability and
keeps incomplete historical SState evidence visibly `NOT READY`.
It separately shows the current research layer: 120 pre-registered candidates
across four families and three horizons, six Edge validation methods, Shadow
feature-group ablations and the still-undefined parameter-sweep framework.
That projection remains synthetic/research-only and cannot promote a model.

`web/data/research-evidence.json` defines the fail-closed display contract for
Paper Positions and Backtest Evidence. The checked-in fixture contains no
positions or backtests and keeps backtest admission false. Future generated
evidence may populate those arrays only when its Repository lineage and
paper-only safety boundary are supplied; the browser rejects an unsafe contract
instead of inferring data from other research artifacts.

`web/data/research-evidence.schema.json` freezes that browser contract. It
requires `authority=false`, provider and dataset lineage for backtests, a
64-character run SHA, and an all-false safety boundary. The schema does not
authorize a producer, R2 access, holdout access, backtest admission, trade plans
or live trading. Until a separately versioned Repository authority exists, CI
publishes only the fail-closed empty fixture.

## Views

- Overview
- Data Health
- Signals shell
- Strategy and SState boundary
- Paper Positions evidence contract
- Paper Trades shell
- Performance Center shell
- Backtests evidence contract
- Risk & Gates

## Deployment shape

The `web/` directory is intentionally static. GitHub Actions builds the normalized authority view and deploys it to GitHub Pages. No client-side private API or secret-bearing backend is required.

GitHub Pages does not apply the Netlify/Cloudflare-style rules in
`web/_headers`. That file is retained only as a defense-in-depth template for a
future header-aware static host. The Pages deployment instead enforces the
policies that HTML can enforce directly: a restrictive Content Security Policy
meta element and `Referrer-Policy: no-referrer` through the document's referrer
meta element. Response-header-only controls such as `frame-ancestors`,
`X-Frame-Options`, `X-Content-Type-Options` and `Permissions-Policy` are not
claimed as enforced on GitHub Pages.

The active cloud-garden image is the only large visual asset in the current
tree and Pages artifact. Styles, scripts and images live under typed
`web/assets/` subdirectories; Repository projections remain under `web/data/`
because several frozen V0.10/V0.11 contracts reference those exact paths.

## Safety

The dashboard contains no real-money order action, no private exchange execution endpoint and no live-trading control. `PAPER-ONLY` is visible in the interface and provider provenance remains explicit.
