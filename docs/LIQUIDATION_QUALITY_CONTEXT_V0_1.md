# Liquidation Quality Context V0.1

Status date: 2026-09-19

Status: **PREPARED CONTRACT ONLY / NO NETWORK**

## Purpose

This contract follows the AgentFeed V0.1 evaluation without installing,
executing or paying for AgentFeed.

Its job is deliberately narrow: normalize already-supplied liquidation events
while preserving the two pieces of information most likely to cause a false
research conclusion if they are lost:

1. **venue-specific coverage quality**;
2. **position-side liquidation semantics**.

The reviewed source is pinned to:

`seekdaseek/agentfeed@0e1db87a65dc0cc0b890c2257e10e12cd3966cf7`

Evaluation receipt:

`research/receipts/2026-09-19-agentfeed-evaluation-v0-1.json`

## Input boundary

V0.1 accepts only:

- `synthetic_fixture`;
- `existing_non_holdout_fixture`.

It does not call AgentFeed, exchanges, x402, wallets, R2 or holdout storage.

Every event preserves:

- exchange;
- symbol;
- coverage quality;
- explicit position-side liquidation meaning;
- event timestamp;
- observed timestamp;
- available timestamp;
- price;
- quantity;
- computed USD notional.

The causal ordering must be:

```text
event_timestamp_ms
    <= observed_at_ms
    <= available_at_ms
    <= as_of_ms
```

## Side semantics

Only these values are accepted:

- `LONG_LIQUIDATED`;
- `SHORT_LIQUIDATED`.

Generic `BUY` / `SELL` is rejected.

That matters because the reviewed upstream collector explicitly normalizes
different exchange conventions. Binance raw liquidation order side is not the
same semantic object as position side.

This contract therefore refuses to carry ambiguous labels forward.

## Venue coverage quality

The contract records the reviewed upstream claims as provenance-qualified
labels:

| Venue | V0.1 profile |
| --- | --- |
| Bybit | `UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED` |
| Binance | `UPSTREAM_DECLARED_THROTTLED_SNAPSHOT` |
| OKX | `UPSTREAM_DECLARED_THROTTLED_UPDATE` |

These labels are not independent certification by Crypto Autopilot.

A caller may downgrade any venue to:

`DEGRADED_OR_UNKNOWN`

but may not upgrade or relabel a venue into another venue's stronger profile.

This is intentional: a capture outage or incomplete fixture must be allowed to
be less trusted, never silently more trusted.

## No cross-venue total yet

V0.1 does not produce a cross-venue liquidation total or severity score.

That remains closed because Binance and OKX observations are structurally
different from the upstream-declared Bybit coverage. Summing them without a
validated missingness model could create false precision.

A future research version may compare venue-local summaries, but only after
explicit missingness and weighting tests.

## Notional consistency

USD notional is computed from:

```text
price * quantity
```

If a caller also supplies `notional_usd`, the supplied value must match the
computed value within a small numerical tolerance or the row fails closed.

## Duplicate handling

Exact duplicate events fail closed rather than using last-write-wins behavior.

The duplicate key includes:

- venue;
- symbol;
- position-side liquidation semantic;
- event timestamp;
- price;
- quantity.

## Interpretation

Every snapshot is explicitly:

`DESCRIPTIVE_LIQUIDATION_CONTEXT_ONLY`

It is not:

- a squeeze score;
- a cascade score;
- a trade direction;
- a Strategy Router input;
- a Daily Opportunity score;
- candidate-generation authority;
- strategy-selection authority;
- a formal backtest gate;
- a paper-order instruction;
- a real-order instruction.

## Authority

Authorized:

- deterministic normalization of caller-supplied fixture evidence;
- exact AgentFeed evaluation provenance;
- causal timestamp validation;
- explicit venue-quality preservation;
- explicit LONG/SHORT liquidation semantics;
- malformed/duplicate/wrong-symbol rejection.

Not authorized:

- AgentFeed endpoint calls;
- MCP runtime;
- provider API keys;
- wallet creation/funding;
- private-key access;
- x402 payment;
- cross-venue aggregation;
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
