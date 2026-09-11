# Simulation Funding Admission V0.1

Status: **PREPARED OFFLINE VALIDATION — NOT PRODUCTION SIMULATION-DATA ADMISSION AUTHORITY**

## Purpose

Close the software gap between the bounded Pionex funding-history capture and the existing Simulation Readiness V0.3 paper backtest.

The bridge accepts only the exact secret-free PASS report emitted by the reviewed Pionex funding workflow, validates it fail-closed, converts observations to the canonical `FundingPoint` type, and passes those points into the existing `run_long_backtest` engine.

It does not introduce a second broker, a second cost model, provider requests, R2 access, or a new strategy.

## Exact input contract

Funding evidence must match all of the following:

- schema `pionex-funding-history-run-report-v0.1`;
- provider `pionex_public_futures`;
- symbol `BTC_USDT_PERP`;
- 2026-08-01T00:00:00Z inclusive through 2026-08-28T00:00:00Z exclusive;
- protocol SHA-256 `9117e707203b35ef9d7420b96033cd339b97c549f03e3cdae2ecece4637b6834`;
- execution SHA-256 `d2cdafc5900573eb7d9971b7e3d7b9e5e34f50d16a510b56dcd7e0512b5e3315`;
- GitHub `workflow_dispatch` on `refs/heads/main`, attempt 1;
- at most three provider requests and zero automatic retries;
- left boundary proven;
- no API key/private API;
- no R2 or holdout access;
- no simulation-data admission or live-trading claim in the source report.

Every funding observation must preserve the exact symbol, use a finite rate, remain inside the fixed half-open window, and have a strictly increasing unique provider timestamp. No cadence is invented and no missing funding event is zero-filled.

## Simulation path

The bridge reuses:

1. Simulation Readiness V0.3 receipt-bound K-line verification;
2. the existing candle-derived 4H/60M/15M LONG-plan generator;
3. canonical `FundingPoint` values;
4. the existing deterministic risk engine;
5. the existing paper backtest with fee, slippage, funding, stop, kill-switch and max-holding behavior.

A successful offline bridge test removes `historical_funding_evidence_missing` from the software-path blocker set, but it replaces that blocker with `production_simulation_data_admission_not_authorized`.

## Readiness boundary

This stage never emits `FULL_SIMULATION_READY`.

Real funding evidence must first exist from a reviewed `main` manual dispatch. A later separately reviewed production simulation-data admission authority must then bind the exact K-line evidence and exact funding report before a real simulation result can be promoted to a formal readiness decision.

## Authority

Allowed:

- synthetic/offline fixture validation of the exact bridge contract.

Not authorized:

- provider requests;
- production K-line reads;
- production funding-report admission;
- R2 reads/writes;
- replacement-holdout access;
- training/model promotion;
- formal backtest admission;
- strategy/source-switch changes;
- trade plans;
- real-money orders;
- live trading.

Config SHA-256: `b9871ca38bcb69d0850effc4ea56c9e43ff710e798a73966425b000f83521f6c`.
