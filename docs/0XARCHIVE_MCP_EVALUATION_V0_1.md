# 0xArchive MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH ONLY / NOT APPROVED FOR RUNTIME**

## Candidate

Registry capability: `0xarchive_mcp`

Reviewed upstream:

`0xArchiveIO/0xarchive-mcp@5c0531cb685779b5fa8cbff3443f9a7f74fed659`

License: MIT.

## Verified architecture

The reviewed branch is a hosted-MCP documentation repository. It does not ship
the implementation of the remote market-data server.

The documented server is:

`https://mcp.0xarchive.io/mcp`

Access uses browser OAuth with a 0xArchive account and the
`mcp:market.read` permission. The upstream explicitly says not to substitute
an API key or manually pasted bearer token.

The project registry credential metadata is therefore narrowed from generic
service-dependent authentication to `OAUTH_ACCOUNT_MCP_MARKET_READ`. This
does not authorize connecting an account.

## Market-data scope

The documented service covers:

- Hyperliquid core perpetuals;
- Hyperliquid Spot;
- HIP-3 builder perpetuals;
- HIP-4 outcome markets;
- Lighter.

Depending on venue/dataset, the service exposes market summaries, trades,
candles, funding, open interest, liquidations, L2/L3/L4 order books, order
history/order flow, trigger orders and market discovery.

This coverage is potentially valuable as a **historical challenger** because it
adds venues and market-structure datasets not represented by the project's
canonical Binance/Pionex research history.

It is not a source switch.

## Data-quality value

The strongest differentiator for Crypto Autopilot is the documented quality
surface: coverage, freshness, incidents, latency and status.

Those fields are useful for answering a narrower question before any comparison:

> Was the requested venue/dataset actually observed with adequate coverage in
> the requested UTC interval?

A future research adapter should preserve these quality records beside every
derived comparison instead of treating an empty/partial response as a complete
dataset.

Long histories are explicitly documented as paginated/windowed. A returned page
must never be interpreted as the complete interval unless pagination and
coverage establish that fact.

## Liquidation boundary

0xArchive documents both liquidation data and projected forced-liquidation price
levels.

These are different evidence classes:

- recorded liquidation observations may be considered event-data candidates
  only after their schema, side semantics, timing and coverage are validated;
- projected forced-liquidation levels are derived estimates and must remain
  separate from observed liquidation events.

Neither class can be mixed directly into the existing liquidation pipeline
without a versioned adapter and an equivalence/coverage review.

No 0xArchive observation is used here to estimate Binance/Bybit/OKX missingness
or to create cross-venue correction weights.

## Cross-venue comparisons

The upstream documentation itself recommends retaining each source's units and
timestamp when comparing funding across venues.

Crypto Autopilot should additionally preserve venue, instrument type,
observation/availability/retrieval timestamps, coverage status and pagination
completion.

Hyperliquid and Lighter measurements are not interchangeable with Binance or
Pionex. They can challenge or contextualize results, not silently replace the
canonical source.

## Auditability

Because the pinned repository contains documentation rather than server
implementation, service-side normalization, collection and quality calculations
cannot be independently verified from this repository alone.

The service is therefore evaluated as a provider candidate, not as an
implementation/reference library.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Potential future value:

- historical Hyperliquid/Lighter challenger data;
- coverage/freshness/incident evidence;
- independent funding/OI/liquidation comparisons;
- deeper order-book research.

Current action:

- keep exact provenance;
- keep runtime disconnected;
- preserve existing Binance/Pionex authority;
- do not feed hosted data directly into Strategy Router or trading decisions.

Evaluation receipt:

`research/receipts/2026-09-19-0xarchive-mcp-evaluation-v0-1.json`

## Authority

This evaluation grants no OAuth login, account access, paid-plan use, remote MCP
execution, bulk download, WebSocket use, source switch, liquidation aggregation
or correction, Strategy Router/Daily Opportunity integration, R2/holdout access,
training/model promotion, Portfolio Admission, order authority or real live
trading.
