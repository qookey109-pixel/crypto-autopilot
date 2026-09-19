# Depthy MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH ONLY / NOT APPROVED FOR RUNTIME**

## Candidate

Registry capability: `depthy_mcp`

Reviewed upstream:

`depthy-io/depthy-mcp@6c7c23839635dd4c8addb5ed23604d6a3373efdc`

Package version: `0.1.0`.

License: MIT.

## Verified architecture

The pinned repository is a thin MCP/REST client for the hosted Depthy service.
It contains the tool routing and HTTP client, but it does not contain the core
calculation methodology that produces order-book imbalance, liquidity-wall
classification, liquidation clusters or Polymarket smart-money signals.

Runtime requires `DEPTHY_API_KEY`. The server sends it as a Bearer credential
to the configured Depthy base URL. The README documents a free key and the
client's rate-limit error documents a free-tier limit of 30 requests/minute and
100 requests/day. Some endpoints, including multi-symbol comparison, may require
a Pro key.

No API key or remote endpoint is used by this evaluation.

## Hyperliquid scope

The crypto market-structure tools are explicitly Hyperliquid-oriented. Symbols
are normalized to `SYMBOL-PERP` and most market endpoints call Hyperliquid
paths.

Useful contextual surfaces include:

- order-book depth;
- recent depth snapshots;
- resting liquidity walls;
- price/volume/funding/open interest;
- open-interest change.

These can be useful as **source-labelled Hyperliquid context**. They must not be
generalized into Binance, Pionex or global-market facts.

A future adapter would have to retain at least:

- provider = Depthy;
- upstream venue = Hyperliquid;
- symbol and instrument type;
- observation/availability time;
- retrieval time;
- freshness/age;
- raw-versus-derived field classification.

## Liquidation cluster boundary

`get_liquidation_clusters` returns hosted Depthy-derived "liquidation cascade
risk zones".

The pinned GitHub repository does not expose the underlying event set, coverage
model, estimation formula or validation procedure for those zones.

Therefore a cluster is not equivalent to the project's normalized liquidation
event evidence. It cannot be:

- counted as a verified liquidation event;
- mixed into venue-local liquidation event totals;
- used to infer real missingness;
- used to calibrate cross-venue weights;
- used as a squeeze/cascade trading signal.

If studied later, it should enter as a distinct derived-context type with
explicit Depthy provenance.

## Polymarket boundary

The MCP also exposes active Polymarket markets, top-wallet rankings and
"smart-money signals".

Those are interpreted external outputs. The pinned repository does not contain
the backend methodology that creates the signals or wallet ranking.

They are outside the current crypto-exchange execution path and have no Strategy
Router, Daily Opportunity, portfolio or execution authority.

## Auditability

The local server implementation is easy to inspect: it normalizes arguments and
forwards requests to hosted endpoints.

The important market intelligence itself is not locally auditable from this
repository. For this reason the service is better treated as a provider
candidate than as an implementation/reference library.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Potential future value:

- source-labelled Hyperliquid microstructure context;
- independent funding/OI/depth observations;
- derived liquidation-cluster research kept separate from event-level
  liquidation evidence.

Not justified now:

- duplicating the existing liquidation pipeline around opaque cluster outputs;
- cross-venue aggregation;
- accepting Polymarket or cluster "signals" as trading authority.

Evaluation receipt:

`research/receipts/2026-09-19-depthy-mcp-evaluation-v0-1.json`

## Authority

This evaluation grants no Depthy API-key access, remote MCP/REST execution,
paid-plan use, source switch, cross-venue weighting, signal generation,
Router/Daily Opportunity integration, R2/holdout access, training/model
promotion, portfolio admission, real-money orders or real live trading.
