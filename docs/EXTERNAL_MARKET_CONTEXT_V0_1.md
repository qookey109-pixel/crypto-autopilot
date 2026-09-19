# External Market Context V0.1

Status date: 2026-09-19

Status: **PREPARED PREFETCHED-EVIDENCE INGESTION ONLY / NO NETWORK CAPTURE**

## Purpose

This layer adds six external crypto-context sources to the Qookey Crypto
Autopilot architecture without embedding third-party MCP runtimes into the
trading process and without granting new provider authority.

The goal is to let upstream capture or operator tooling eventually provide
market-context evidence in a stable internal shape while keeping Strategy
Router V0.1 deterministic and no-I/O.

## Registered sources

| Source | Pinned upstream | Intended role |
| --- | --- | --- |
| Crypto Orderbook MCP | `kukapay/crypto-orderbook-mcp@29a1410482a378e8f49baee289c5a9d3a200074e` | bid/ask depth, imbalance, mid-price and cross-exchange market structure |
| Crypto Liquidations MCP | `kukapay/crypto-liquidations-mcp@d9a02cda38bdb0f3556fe9a112997f29c82e1900` | recent liquidation-event pressure |
| Pulse Verity | `PulseBet/pulse-verity@a81ab1d4b645537c6af62159a940fe1cd614954c` | signed external price cross-check and historical settlement print verification |
| Crypto RSS MCP | `kukapay/crypto-rss-mcp@2cc6a514bfe1c028ddf55193dcfa1073ae2ab3fe` | news/event context |
| Crypto Sentiment MCP | `kukapay/crypto-sentiment-mcp@a002ecef5cdd5351e3dd8e03f50c87ef48e3f7dc` | sentiment balance, social volume/dominance and social trend context |
| Crypto Trending MCP | `kukapay/crypto-trending-mcp@2bc2349ac606e3677f877de32d82a47cd1f6b86d` | discovery/trending context |

All six upstream repositories are MIT-licensed at the pinned review point.

## Why the MCP server code is not vendored

The project needs stable domain evidence, not a permanent dependency on one MCP
transport implementation.

V0.1 therefore records exact upstream provenance and implements a native,
no-I/O normalizer. It does **not** copy the third-party server code into
`src/`, start MCP subprocesses, install Playwright, store API keys or call
Santiment/Pulse/exchange endpoints.

That avoids coupling Strategy Router to:

- MCP transport lifecycle;
- upstream Markdown rendering;
- browser automation;
- API-key management;
- one third-party release cadence.

## Normalized evidence envelope

Each already-fetched row supplies:

- `source_id`;
- normalized system `symbol` when the source is asset-specific;
- `observed_at_ms`;
- `available_at_ms`;
- a source payload.

The builder treats RSS titles and social/trending words as **untrusted external data**.
They never gain instruction authority, and V0.1 bounds their length and rejects
control characters.

The builder rejects:

- unsupported sources;
- duplicate source rows;
- wrong-symbol evidence;
- evidence available after the decision timestamp;
- evidence claiming availability before observation;
- malformed source-specific metrics;
- Pulse prints timestamped after the decision time;
- overlong/control-character external text.

The result is
`qookey-external-market-context-snapshot-v0.1`.

## Current normalization

### Order book

Preserves:

- exchange;
- bid depth;
- ask depth;
- imbalance in [-1, 1];
- positive mid price.

### Liquidations

V0.1 aggregates already-fetched BUY/SELL liquidation events into:

- event count;
- BUY notional;
- SELL notional;
- gross notional;
- side imbalance.

The layer deliberately does not reinterpret BUY/SELL into a trading direction.
That semantic mapping requires a separate reviewed strategy rule.

### Pulse Verity

Preserves:

- price;
- grade;
- signature verification result;
- print timestamp.

A false signature-verification flag is preserved as false. The normalizer never
upgrades or fabricates verification.

### RSS

Preserves a bounded set of titles, article count and latest publication time.
Future-dated articles fail closed relative to the decision timestamp.

### Sentiment

Accepts the metrics exposed by the upstream research source:

- sentiment balance;
- social volume;
- social dominance;
- trending words.

No sentiment threshold is connected to Router V0.1.

### Trending

Preserves rank plus supplied numeric market context such as 1h/24h/7d change,
24h volume and market cap.

Trending rank is context only. It cannot automatically add an asset to a live
or paper candidate basket in V0.1.

## Architecture placement

~~~text
External public/research sources
  Orderbook / Liquidations / Pulse / RSS / Sentiment / Trending
        ↓
separately authorized capture or operator-provided evidence
        ↓
External Market Context V0.1
  causal validation + normalization
        ↓
research evidence available to future Router/Opportunity versions
~~~

Existing Daily Opportunity Engine V0.1 and Strategy Router V0.1 behavior remains
unchanged by this version.

## Authority

Authorized:

- source provenance registry;
- exact upstream commit pins;
- ingestion of caller-supplied/prefetched evidence;
- deterministic source-specific normalization;
- anti-leakage and wrong-symbol validation.

Not authorized:

- network capture;
- embedded MCP runtime;
- API-key storage;
- external text instruction authority;
- Strategy Router threshold changes;
- Daily Opportunity score changes;
- automatic candidate generation;
- automatic strategy selection;
- R2 writes;
- replacement holdout;
- training;
- model promotion;
- real-money orders;
- real live trading.
