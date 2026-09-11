# Pionex Funding History Execution V0.1

Status: **AUTHORIZED AFTER PROTECTED-MAIN MERGE — AWAITING WORKFLOW WIRING**

## Purpose

Capture the exact public Pionex funding-rate history needed to remove the current `historical_funding_evidence_missing` blocker for the existing BTC V0.2 capacity-sample window.

This is intentionally narrower than a full funding database. It is one bounded public capture for `BTC_USDT_PERP` from `2026-08-01T00:00:00Z` inclusive through `2026-08-28T00:00:00Z` exclusive.

## Provider contract

- endpoint: `GET /api/v1/market/fundingRates`
- authentication: none / public market data
- symbol: `BTC_USDT_PERP`
- page limit: 500
- maximum provider requests: 3
- retries: 0
- request pace: 3 requests/second
- timeout: 15 seconds

The prepared collector does not assume a fixed 4h/8h funding cadence and never fills missing observations with zero.

## Completeness

The capture passes only when pagination proves the left boundary is reached/crossed and at least one valid in-window observation exists.

Every observation must:

- match the exact symbol;
- have a unique provider timestamp;
- have a finite funding rate;
- remain at or before the request cursor.

Provider failure, empty history before the left boundary, duplicate timestamps, non-finite values, symbol mismatch, or request-budget exhaustion fails closed.

## Output

The eventual workflow artifact may include normalized public observations:

- symbol;
- funding timestamp;
- funding rate;
- request count;
- first/last in-window timestamp;
- left-boundary proof.

Raw provider payloads are not retained. No API key or account data is involved.

## Execution boundary

The runner requires:

- GitHub Actions;
- `workflow_dispatch`;
- `refs/heads/main`;
- repository `qookey109-pixel/crypto-autopilot`;
- run attempt 1;
- execution between `2026-09-11T00:00:00Z` and `2026-09-16T00:00:00Z` exclusive.

This stacked PR deliberately does not add workflow wiring. A later minimal wiring change can expose the runner after the protocol and execution package are reviewed onto `main`.

## Explicit non-authority

This stage does not authorize:

- private Pionex API access;
- API-key use;
- R2 reads/writes;
- replacement-holdout access;
- simulation-data admission;
- formal backtest admission;
- training;
- strategy/source-switch changes;
- trade plans;
- real-money orders;
- live trading.

A PASS funding capture is evidence for a later reviewed simulation-data admission step; it does not make the simulation automatically READY.

Protocol config SHA-256: `9117e707203b35ef9d7420b96033cd339b97c549f03e3cdae2ecece4637b6834`
Execution config SHA-256: `d2cdafc5900573eb7d9971b7e3d7b9e5e34f50d16a510b56dcd7e0512b5e3315`
