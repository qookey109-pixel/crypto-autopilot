# Qookey Crypto Autopilot Dashboard V0.1

## Goal

Create a read-only operational and research dashboard for Qookey Crypto Autopilot without exposing exchange keys, Cloudflare R2 credentials, private Pionex APIs or any live-trading control.

The first website release is a monitoring / performance center only.

## V0.1 pages

### 1. Overview

- project mode: `PAPER-ONLY`
- live trading authorization: false
- provider-equivalence gate state
- latest data-materialization states
- strategy replay readiness
- paper broker readiness
- latest backtest summary
- current risk-gate summary

### 2. Markets / Data Health

For each tracked market:

- provider
- symbol
- Trade `15M / 60M / 4H` coverage
- Mark Price coverage
- Funding coverage
- first / last observed timestamp
- archive / partition audit state
- gap / revision warnings
- materialization state

Provider provenance must remain visible. Binance data must never be displayed as Pionex-native history.

### 3. Signals

Read-only strategy output:

- symbol
- LONG / SHORT / FLAT intent
- confidence / score
- timeframe inputs
- SState regime
- signal timestamp
- risk-gate decision

No order button is included in V0.1.

### 4. Paper Positions

Once the production-grade paper broker lifecycle is ready:

- open paper positions
- entry price
- mark price
- unrealized P&L
- realized P&L
- funding P&L
- stop / take-profit simulation state
- exposure by symbol

### 5. Paper Trades

- paper trade history
- entry / exit
- direction
- size
- fees
- funding
- realized P&L
- strategy / signal linkage

### 6. Performance Center

- equity curve
- cumulative return
- daily / weekly / monthly P&L
- win rate
- profit factor
- max drawdown
- Sharpe-like research metric where authorized
- trade count
- long vs short performance
- per-symbol contribution
- funding contribution

### 7. Backtests

- dataset authority used
- provider
- universe
- time window
- parameter-set identity
- run receipt / SHA
- metrics
- admission status

The UI must distinguish `READY`, `PASS`, `PENDING`, `REVIEW_REQUIRED`, `NOT_READY`, and `NOT_AUTHORIZED`.

### 8. Risk & Gates

- source / provider equivalence
- historical-universe admission
- liquidity admission
- SState readiness
- parameter freeze
- R2 budget gate
- strategy replay readiness
- paper broker readiness
- live-trading gate

A blocked gate must never be visually presented as a soft warning.

## Architecture

### Frontend

Static web application deployed separately from the Python research package.

Suggested repository path:

`web/`

The browser only receives public/safe dashboard JSON. It never receives:

- Pionex API secrets
- R2 S3 keys
- Cloudflare account secrets
- private exchange responses
- unrestricted raw R2 bucket access

### Dashboard API

A small server-side API layer exposes normalized read-only snapshots such as:

- `/api/status`
- `/api/data-health`
- `/api/signals`
- `/api/paper/positions`
- `/api/paper/trades`
- `/api/performance`
- `/api/backtests`
- `/api/gates`

The API reads only authorized summaries / receipts / manifests and later paper-trading state.

### Storage separation

- R2: historical Parquet, manifests and immutable evidence
- D1 or another small index store: dashboard-friendly current snapshots / indexes when required
- browser: no direct private R2 credentials

The dashboard must not infer Pionex provenance from Binance storage keys.

## V0.1 source-of-truth rule

The dashboard is a view, never the authority.

Repository receipts / immutable evidence remain authoritative. If UI state conflicts with a frozen receipt, the UI must show an error / stale-state warning rather than rewrite the authority.

## Security boundary

V0.1 is deliberately read-only:

- `source_switch_authorized=false`
- `pionex_native_relabel_authorized=false`
- `backtest_admission` shown exactly as authority states
- `trade_plan_authorized=false`
- `live_trading_authorized=false`

No real-money execution control appears in V0.1.

## Delivery phases

### Dashboard D1 — Static Shell

- responsive desktop/mobile layout
- navigation
- Overview
- Data Health
- Gates
- mock-safe fixtures matching current receipt schemas

### Dashboard D2 — Authority Snapshot API

- server-side receipt / manifest normalization
- safe JSON endpoints
- stale-state / missing-authority handling

### Dashboard D3 — Research Views

- Backtests
- Signals
- Performance
- historical coverage charts

### Dashboard D4 — Paper Broker Views

Only after the paper broker lifecycle / reconciliation authority is ready:

- paper positions
- paper trades
- paper P&L
- funding attribution

### Dashboard D5 — Production hardening

- authentication if private deployment is selected
- audit logging for administrative actions
- caching / rate limits
- deployment receipt
- smoke / browser tests

## Definition of V0.1 website PASS

- builds reproducibly
- no secrets bundled into frontend artifacts
- Overview / Data Health / Gates render from real normalized authority snapshots
- stale / missing authority states fail visibly
- provider provenance is always visible
- no live-order endpoint or live-order UI exists
- mobile and desktop smoke tests PASS
