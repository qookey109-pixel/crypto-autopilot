# Pionex Research Universe 150+ V0.1

Status: **PREPARED — NOT EXECUTION AUTHORITY**

## Purpose

Prepare the deterministic selection layer that turns a Pionex perpetual-market
snapshot into a research universe of at least 150 quality-valid markets.

This stage is intentionally broader than the existing BTC-only historical pilot
and narrower than historical materialization. It selects markets and assigns
data-acquisition profiles; it does not call Pionex, read/write R2, open the
replacement holdout, train models, or trade.

## Universe semantics

The output combines three provider-separated labels:

1. **Crypto Core 100** — the 100 quality-valid Pionex crypto perpetuals with the
   highest observed 24h quote amount. Spread, trade count and symbol are
   deterministic tie-breakers.
2. **Meme candidates** — every quality-valid live Pionex perpetual whose base
   asset intersects the explicit versioned meme watchlist. This tag is research
   metadata, not an investment endorsement.
3. **Alternative assets** — every quality-valid live Pionex perpetual that
   intersects the existing SHA-bound tokenized-equity / ETF-fund / metals
   registry.

The union is filled with the next liquidity-ranked crypto markets until it has
at least 150 markets. The count is a minimum, not an exact cap: live meme and
alternative-asset registry matches are retained even when the union exceeds 150.

## Important Top-100 distinction

This V0.1 `crypto_core` is **Pionex-liquidity ranked**, not a claim that these are
the global top 100 cryptocurrencies by market capitalization.

Pionex public futures tickers provide trading activity, not global market cap.
A literal market-cap Top 100 requires a separately versioned public rank source
and symbol/identity mapping. This stage refuses to manufacture that claim.

For the 2026-09-15 simulation target, the liquidity-ranked Pionex core is the
execution-oriented universe. A market-cap breadth layer can be added without
changing Pionex execution provenance.

## Market-quality join

The future execution stage must take one consistent public snapshot from:

- live Pionex PERP symbols;
- Pionex PERP tickers;
- Pionex PERP book tickers.

A market is quality-valid only when it has the required ticker/book records,
finite positive close/bid/ask values, non-negative quote amount and trade count,
and a non-crossed book. No hard spread threshold is invented at this prepared
research stage. Invalid or missing markets are reported and excluded rather
than silently repaired.

## Tiered historical acquisition

Selecting 150+ markets does **not** mean downloading every intraday timeframe
for every market.

- `FULL_INTRADAY` — at most 30 highest-ranked selected markets:
  `15M / 60M / 4H / 1D / 1W`.
- `MULTISCALE_RESEARCH` — remaining Crypto Core and explicit meme candidates:
  `60M / 4H / 1D / 1W`.
- `BREADTH_BACKGROUND` — remaining selected markets, including most tokenized
  alternative assets: `1D / 1W`.

`1Y` remains a later derived timeframe from validated `1D`; Pionex does not
provide a native 1Y K-line interval and this stage does not authorize yearly
aggregation.

The purpose of the profiles is to keep the 150+ universe broad while bounding
API/R2 cost and reserving expensive `15M` history for the markets most likely to
enter simulation.

## Existing lineage

- Binance USD-M Crypto Core 100 remains a provider-separated four-year research
  dataset. It is not relabeled as Pionex-native.
- Pionex Alternative Assets V0.1 remains the classification registry for
  tokenized equities, funds and metals. Its exact bytes are SHA-bound here.
- Pionex Historical Reach V0.3 separately measures native history depth by
  timeframe. Reach evidence determines later materialization lengths; universe
  selection does not assume every market has the same historical depth.

## Prepared-only boundary

This PR validates deterministic selection only with synthetic fixtures.

It does **not** authorize:

- public Pionex network requests;
- private/account API access;
- R2 reads or writes;
- 150+ historical materialization;
- replacement-holdout access;
- training or formal backtest admission;
- strategy changes or source switching;
- trade plans, real-money orders or live trading.

A later reviewed execution authority must bind the exact public snapshot inputs
before a real 150+ universe is frozen.

Config SHA-256: `3c70bab735b76f59766cfbea9f2c1e8cbb24305359f5f877eb2782a1445b6309`
