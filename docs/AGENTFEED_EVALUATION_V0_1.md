# AgentFeed Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH ONLY / NOT APPROVED FOR RUNTIME**

## Candidate

Registry capability:

`agentfeed`

Reviewed upstream:

`seekdaseek/agentfeed@0e1db87a65dc0cc0b890c2257e10e12cd3966cf7`

License: MIT.

## Useful part for Crypto Autopilot

The strongest value is the liquidation-data methodology, not the payment rail.

The reviewed collector records USDT-perpetual liquidation events from:

- Bybit;
- OKX;
- Binance.

It also normalizes exchange-specific side semantics before storing the rows.

That makes the upstream project useful as a reference for two future internal
contracts:

1. liquidation coverage-quality metadata;
2. explicit long-liquidated / short-liquidated semantics.

## Important data-quality limitation

Upstream explicitly documents materially different coverage quality by venue.

At the reviewed commit:

- Bybit is described as the highest-integrity / complete stream;
- Binance is sampled by the exchange liquidation feed;
- OKX is rate-limited / sampled.

Therefore a future Crypto Autopilot liquidation context must never treat a
cross-venue aggregate as if every venue had equal observation completeness.

The internal shape should carry a field such as:

```text
venue
coverage_quality
coverage_notes
side_semantics
observed_at_ms
available_at_ms
```

before any aggregate is produced.

## Side semantics

The reviewed code converts exchange-specific liquidation messages into a common
position-side interpretation.

The important rule for this project is:

```text
LONG_LIQUIDATED
SHORT_LIQUIDATED
```

not generic BUY / SELL.

BUY / SELL is too ambiguous because some exchange feeds expose order side while
others expose position side.

No liquidation-side field should be interpreted as a trade direction without a
separate validated rule.

## Cascade / squeeze / crowding outputs

AgentFeed also exposes interpreted outputs including cascade severity, crowding
reads and composite squeeze-style scores.

Those are useful challenger concepts, but they embed upstream choices and
thresholds.

V0.1 therefore does not permit them to:

- select a strategy;
- change Strategy Router thresholds;
- alter Daily Opportunity scoring;
- generate an automatic candidate;
- authorize a paper or real trade.

## Payment and wallet boundary

The hosted paid surface uses x402 and USDC.

The reviewed MCP server builds payment requirements and records payer-wallet /
settlement metadata after payment. Upstream documentation also describes client
flows that use a funded wallet/private key for automatic per-call payment.

Crypto Autopilot currently grants none of those authorities.

This evaluation does not:

- create a wallet;
- fund a wallet;
- read or store a private key;
- make a paid AgentFeed call;
- enable x402;
- call even the hosted free endpoints.

That keeps the current zero-cost and secret-isolation boundary intact.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Recommended next step:

Build a native no-network liquidation-quality contract using synthetic or
existing non-holdout fixtures only.

Require:

- explicit venue;
- explicit coverage quality;
- explicit position-side liquidation semantics;
- causal timestamps;
- no directional-trade interpretation;
- zero payment/runtime authority.

Evaluation receipt:

`research/receipts/2026-09-19-agentfeed-evaluation-v0-1.json`

## Authority

This evaluation grants no network, wallet, private-key, payment, provider, R2,
holdout, training, promotion, Router, trade-plan, order or real-live-trading
authority.
