# Pionex Historical Research Pool V0.1

## Status

`PREPARED_NOT_AUTHORIZED` on 2026-09-10.

This document prepares a first **150-market Pionex-native historical research
pool**. It does not start provider requests, read or write R2, create a
schedule, or authorize any trading operation. The executable scope is the
versioned config and its protected-main receipt:

- `config/pionex_historical_research_pool_v0_1.json`
- `research/receipts/2026-09-10-pionex-historical-research-pool-v0-1-authority.json`

## Intended scope

The first execution target is at least 150 currently `TRADING` Pionex USDT
perpetual products, selected from public Pionex market metadata and audited
historical K-lines. If available in Pionex, the classification report may
include:

- crypto assets;
- tokenized equities;
- tokenized metals;
- tokenized ETFs or funds;
- tokenized commodities; and
- other Pionex perpetual products.

The category labels are descriptive. They do not create a product or trading
authority, and a spot-only product cannot enter this perpetual-futures pool.
Classification must come from explicit metadata or be marked
`REVIEW_REQUIRED`; it must not be inferred from a ticker alone.

## History and completeness

The requested intervals are `15M`, `60M` and `4H`. Each symbol keeps its
point-in-time first available timestamp and latest complete UTC candle. A
symbol with a missing interval, unresolved gap, invalid candle or unavailable
history is excluded from the complete pool and reported; it is never silently
interpolated or replaced with Binance data.

The 150 figure is a minimum planning target and preferred first batch, not a
hard upper bound. Additional qualified products may be included only when the
separate execution authority sets a cap and a fresh FREE-ONLY capacity proof
supports it. If fewer than 150 products pass the data and integrity gates, the
result is `INCOMPLETE`, not an artificially filled list. The downstream Crypto
Core 100 must be selected only from complete, audited members and must not be
declared complete from candidate diagnostics or workflow success alone.

## Provider and safety boundary

Pionex remains the provider and provenance authority for this pool. Binance
USD-M, Binance Vision, spot, equities or other external data cannot be spliced
into the Pionex namespace or relabeled as Pionex-native.

Raw history is intended for Cloudflare R2 only after a separate execution
authority, a fresh FREE-ONLY headroom check and exact receipt/SHA readback
contract. Raw history is not projected to GitHub Pages. No private API,
account data, secret, holdout, source switch, model promotion, trade plan,
real-money order or live trading is authorized.

## Gate to execution

Before any cloud run, this prepared scope must be reviewed and merged through
protected `main`, then paired with a separate execution authority bound to the
merged config hash. That authority must specify the serialized shard schedule,
provider-request limit, R2 namespace and write gate, retry/stop behavior,
receipt schema and post-run completeness gate.

The existing frozen 15-symbol Pionex M1/M1A/M1B evidence remains unchanged and
is not reinterpreted as evidence that this 150-market expansion has started.
