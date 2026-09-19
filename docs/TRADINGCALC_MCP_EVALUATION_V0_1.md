# TradingCalc MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH ONLY / NOT APPROVED FOR RUNTIME**

## Candidate

Registry capability:

`tradingcalc_mcp`

Reviewed upstream:

`SKalinin909/tradingcalc-mcp@ca78963c57cba09d599be3f28363695132b479b9`

Version: `2.9.1`.

License: MIT.

## What was verified

At the reviewed commit, the public repository documents 31 tools spanning trade
planning, risk/margin, funding/carry, market profile, primitives, an integrated
pre-trade workflow, on-chain helpers, prediction-market helpers and
`system.verify`.

The published MCP surface is a remote Streamable HTTP endpoint at
`https://tradingcalc.io/api/mcp`.

The reviewed README states:

- anonymous access is free with 20 calls/day;
- a free optional bearer API key raises the documented quota to 200 calls/day;
- the MCP/HTTP surface can be used without an exchange private API key for the
  documented calculator requests.

The project registry metadata is corrected accordingly. This does not authorize
calling the endpoint.

## Critical audit limitation

The pinned GitHub repository does **not** contain the core TradingCalc formula
implementation or the source of its claimed 35 canonical verification vectors.

Its root is primarily metadata, documentation and examples. The provided
`examples/risk-agent-wrapper.ts` imports the separate `tradingcalc-sdk` and
calls the hosted service.

Therefore Crypto Autopilot can verify the documented interface and integration
shape at this commit, but it cannot independently prove from this repository
alone that the hosted formulas are equivalent to the project's risk rules.

The upstream statement that calculations are deterministic is useful service
metadata, not a local mathematical proof.

## Best fit for Crypto Autopilot

The useful scope is **challenger / cross-check only** for explicit-input
arithmetic such as:

- PnL;
- break-even;
- liquidation-price estimates;
- position sizing;
- funding cost;
- average entry;
- hedge ratio.

These overlap existing Crypto Autopilot risk and execution layers. They should
not become a second canonical risk authority.

A future controlled comparison could feed the same synthetic/non-holdout inputs
to the project calculator and an external challenger, then record discrepancies.
That would require a separate runtime/network authorization because the reviewed
implementation is hosted.

## Decision-oriented outputs are not authority

The upstream example wrapper exposes:

- `approved`;
- `verdict`;
- `isSafe()`;
- `preTradeGate()`;
- a recommended size and rejection reason.

It explicitly demonstrates using an approved result as a gate before execution.

Those outputs embed upstream defaults and policy choices, including fee,
maintenance-margin and risk thresholds. They must not directly:

- admit a portfolio position;
- override Crypto Autopilot risk limits;
- select a Strategy Router path;
- create a trade candidate;
- authorize paper/live execution;
- authorize a real-money order.

The same boundary applies to prediction-market "edge" and other upstream
go/no-go style outputs.

## Network, secrets and privacy

Actual calculations require the hosted TradingCalc service or its SDK client,
so runtime introduces an external network dependency.

The anonymous tier does not require an API key. An optional bearer key is still
a secret if configured and must not be committed, logged or placed in artifacts.

Trade setup inputs sent to the remote service may contain account balance,
entry, stop, leverage, risk percentage and other strategy parameters. A future
runtime review must explicitly decide whether those fields are permitted to
leave the project boundary.

## Self-verification

`system.verify` is useful as a hosted service self-check, but because the
canonical vectors and core implementation are not present in this pinned
repository, a remote PASS is not equivalent to independent local verification.

It may be recorded as challenger evidence only.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Recommended use now:

- retain exact upstream provenance;
- use the documented formulas/workflows as research references;
- keep project-native risk and portfolio gates authoritative;
- avoid importing the execution-gating wrapper;
- do not call the hosted MCP/HTTP service yet.

Evaluation receipt:

`research/receipts/2026-09-19-tradingcalc-mcp-evaluation-v0-1.json`

## Authority

This evaluation grants no:

- automatic installation or schedule;
- SDK/code import;
- MCP or HTTP runtime;
- external-network call;
- TradingCalc bearer-key use;
- Strategy Router or Daily Opportunity integration;
- Portfolio Admission or execution authority;
- R2 access;
- holdout access;
- source switch;
- training;
- model promotion;
- formal trade-plan authority;
- real-money order authority;
- real live trading.
