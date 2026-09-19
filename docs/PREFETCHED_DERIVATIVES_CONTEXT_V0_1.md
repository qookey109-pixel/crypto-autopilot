# Prefetched Derivatives Context V0.1

Status date: 2026-09-19

Status: **PREPARED CONTRACT ONLY / NO NETWORK**

## Purpose

This contract is the first implementation step after the reviewed
Crypto Market Data MCP evaluation.

It deliberately does not install or execute the upstream MCP server. Instead it
defines a native, deterministic shape for already-fetched derivatives context:

- funding rate and funding interval;
- open interest;
- Binance global long/short account ratio.

The source review is pinned to:

`eliasfire617/crypto-market-data-mcp@7720d7116e26e578037c519d6fdae0d9ba0e8a75`

Evaluation receipt:

`research/receipts/2026-09-19-crypto-market-data-mcp-evaluation-v0-1.json`

## Input boundary

V0.1 accepts only:

- `synthetic_fixture`;
- `existing_non_holdout_fixture`.

Provider capture, MCP runtime calls, R2 reads/writes and frozen/replacement
holdout access remain outside this contract.

Every row must preserve:

- metric kind;
- exchange;
- symbol;
- observed timestamp;
- available timestamp;
- metric payload.

Evidence available after the decision timestamp fails closed.

## Funding

Funding rows preserve:

- raw `funding_rate`;
- `funding_interval_hours`;
- exchange provenance.

V0.1 does not consume an upstream "arbitrage opportunity" or convert funding
spread into a directional instruction.

## Open interest

Open-interest rows preserve one or both of:

- `open_interest_amount`;
- `open_interest_value`.

Values must be finite and non-negative.

Venue coverage is explicit. Missing data is not silently filled from another
exchange.

## Binance long/short ratio

This metric remains Binance-only in V0.1.

Supported periods mirror the reviewed upstream contract:

`5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d`

The normalizer requires:

- a positive long/short ratio;
- long and short shares in `[0, 1]`;
- shares summing to 1;
- ratio consistency with those shares.

This prevents a malformed positioning record from entering research context.

## Duplicate handling

Funding and open-interest rows allow one row per exchange.

Long/short rows allow one row per Binance period.

A duplicate metric/exchange/period row fails closed rather than using
last-write-wins behavior.

## Interpretation

Every snapshot is explicitly:

`DESCRIPTIVE_RESEARCH_CONTEXT_ONLY`

It is not:

- a Strategy Router input yet;
- a Daily Opportunity score input;
- candidate-generation authority;
- strategy-selection authority;
- a formal backtest gate;
- a trade plan;
- a real-order instruction.

A later validation must demonstrate whether any normalized derivatives feature
adds stable out-of-sample information before routing/scoring integration is
considered.

## Authority

Authorized:

- deterministic normalization of caller-supplied fixture evidence;
- exact source/evaluation provenance;
- causal timestamp validation;
- malformed/duplicate/wrong-symbol rejection.

Not authorized:

- external network capture;
- MCP runtime execution;
- exchange/API credentials;
- hosted MCP API credentials;
- Strategy Router integration;
- Daily Opportunity integration;
- automatic candidate generation;
- automatic strategy selection;
- R2 writes;
- holdout access;
- training;
- model promotion;
- formal trade plans;
- real-money orders;
- real live trading.
