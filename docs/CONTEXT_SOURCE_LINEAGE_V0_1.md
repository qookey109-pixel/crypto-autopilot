# Context Source Lineage V0.1

Status: **PREPARED RESEARCH-ONLY SOURCE DECISION / NO PROVIDER EXECUTION**

Observation date: **2026-09-03**

## Purpose

Market Regime / Altcoin Breadth V0.1 already defines the semantics of:

- BTC and ETH closed-price context;
- aggregate crypto market capitalization excluding BTC and ETH (`total3_value` semantics);
- BTC dominance;
- fixed-universe altcoin breadth.

The missing piece is trustworthy source lineage for the market-wide values.
This document freezes a zero-cost source decision without granting permission
to fetch, schedule, store, backfill, tune, promote, or trade.

## Zero-cost constraint

The project budget remains **0 USD/month**. A source that requires a paid API
plan cannot silently become the production or research source. There is no paid
fallback.

Unofficial TradingView/chart endpoints or brittle webpage scraping are also not
accepted as canonical research lineage merely because they appear free.

## Forward current-snapshot candidate: CoinPaprika Free

CoinPaprika is the preferred V0.1 candidate for a future forward collector
because its official Free REST API:

- uses `https://api.coinpaprika.com/v1/`;
- does not require an API key for the free path;
- documents a $0 plan and 20,000 requests/month;
- exposes `/global` with total crypto market capitalization and Bitcoin
  dominance;
- exposes `/tickers/eth-ethereum` with Ethereum market capitalization.

Official documentation reviewed for this decision:

- https://docs.coinpaprika.com/api-reference/global/get-market-overview-data
- https://docs.coinpaprika.com/api-reference/tickers/get-ticker-for-a-specific-coin
- https://docs.coinpaprika.com/api-reference/rest-api/introduction
- https://docs.coinpaprika.com/api-plans

### Same-provider formula

A future authorized capture must construct the semantic values from the same
CoinPaprika observation family:

```text
total_market_cap_usd = /global.market_cap_usd
btc_dominance_pct    = /global.bitcoin_dominance_percentage
btc_market_cap_usd   = total_market_cap_usd * btc_dominance_pct / 100
eth_market_cap_usd   = /tickers/eth-ethereum quotes.USD.market_cap

total3_value = total_market_cap_usd
             - btc_market_cap_usd
             - eth_market_cap_usd
```

A negative `total3_value` is invalid and must fail closed.

This is intentionally a semantic aggregate, not a dependency on a proprietary
chart symbol named `TOTAL3`.

## What this candidate can solve

After a separately reviewed execution authority, periodic current snapshots
could be collected **forward from that authorization date**. Such a collection
could eventually produce a causal 4H/1D context history if every observation
records:

- provider timestamps;
- local capture timestamp;
- exact endpoint identity;
- raw-payload SHA-256;
- component provenance;
- missing or failed captures without interpolation.

This V0.1 decision does **not** create that collector, workflow, R2 namespace,
or schedule.

## Historical global context remains blocked

The project currently has no accepted zero-cost canonical source for the
multi-year historical combination of total crypto market cap, BTC dominance,
and ex-BTC/ETH aggregate market cap.

### CoinPaprika historical per-coin data

CoinPaprika Free documents daily historical ticker data for roughly the last
one year. That is useful for individual assets, but it is not equivalent to a
point-in-time full-market aggregate history.

Reconstructing old global market cap by summing a present-day set of coins would
introduce survivorship and membership distortion. It would also fail the
project's desired multi-year context horizon. Therefore V0.1 rejects this as a
canonical historical-global reconstruction.

Reference:
https://docs.coinpaprika.com/api-reference/tickers/get-historical-ticks-for-a-specific-coin

### CoinGecko official global history

CoinGecko documents `/global/market_cap_chart`, but the official reference says
this endpoint is exclusive to paid subscribers. That conflicts with the
project's zero-cost policy.

Reference:
https://docs.coingecko.com/reference/global-market-cap-chart

CoinGecko's current `/global` endpoint remains useful as an external comparison
candidate in a future review, but it does not solve the zero-cost historical
requirement by itself.

### CoinMarketCap official global history

CoinMarketCap's `/v1/global-metrics/quotes/historical` provides exactly the
kind of historical market-wide metrics desired, including BTC dominance and
total market cap, but current documentation places historical access on paid
plans. It is rejected under the $0 policy.

Reference:
https://coinmarketcap.com/api/documentation/pro-api-reference/global-metrics

## Consequence for current research

Until a separately versioned historical source authority exists:

- Market Regime / Altcoin Breadth V0.1 remains a valid research implementation
  but has no authorized real historical global-context feed;
- Contextual Edge Evaluation V0.1 must not claim real historical regime uplift
  from fabricated or reconstructed global values;
- Crypto Core 100 can later supply its separately governed **exchange-derived
  breadth** component after its own materialization/completeness gates, but that
  does not magically become global market-cap history;
- current snapshots must never be backfilled or carried backward to represent
  earlier dates;
- the frozen replacement holdout remains unopened.

## Why this is preferable to a scraper

A scraper could make a chart appear complete immediately, but it would create
poor scientific lineage: endpoint stability, historical membership, timestamp
semantics, revisions, licensing, and reproducibility would all be unclear.
The project instead preserves `BLOCKED` as a legitimate research result.

## Next eligible engineering step

A future `Context Forward Capture V0.1` may be proposed after separate review.
It should be a bounded, free-only, current-snapshot collector using the frozen
same-provider formula above. Its first observation must be honestly timestamped;
it must not pretend to backfill time before activation.

That future proposal still cannot authorize strategy changes, SHORT execution,
model promotion, trade plans, real-money orders, or live trading.

## Authority boundary

This document grants **no runtime authority**. In particular, all provider
fetch, production R2 read/write, historical backfill, workflow schedule,
holdout, strategy-change, model-promotion, trade-plan, real-money, and
live-trading authorities remain false.
