# Binance Historical Data Source V0.1

Updated: 2026-08-18

## Purpose

This document freezes the first Binance USDⓈ-M historical-data source boundary for Qookey Crypto Autopilot.

Binance is a **research/history provider candidate**. Pionex remains the execution-target exchange and the existing Pionex-native M1/M1A/M1B authority remains unchanged.

A Binance symbol mapping is only a syntactic mapping. It never changes data provenance.

## Non-negotiable provenance rule

- Binance provider id: `binance_usdm`
- execution-target exchange: `pionex`
- Binance data is **not** Pionex-native.
- Binance objects must not be stored under Pionex-native R2 keys.
- Binance observations cannot authorize a Pionex-native Historical Universe record.
- A future strategy-source switch requires a separate overlap/equivalence gate.
- No private Binance API and no live trading are introduced here.

## Official API verification

Official Binance USDⓈ-M documentation was rechecked on 2026-08-18.

### Trade klines

Endpoint: `GET /fapi/v1/klines`

V0.1 uses `15m`, `1h`, and `4h` to correspond to the strategy's `15M`, `60M`, and `4H` layers.

The official endpoint supports `startTime`, `endTime`, and `limit`, with a documented maximum limit of 1500. No fixed historical-retention cap is stated on the endpoint page, so V0.1 treats long-horizon availability as something that must be measured per symbol rather than assumed.

### Funding-rate history

Endpoint: `GET /fapi/v1/fundingRate`

The official endpoint supports inclusive `startTime`, inclusive `endTime`, and a maximum limit of 1000. Results are documented as ascending. If the requested range contains more rows than `limit`, Binance returns rows from `startTime` up to the limit. The endpoint shares a documented 500 requests / 5 minutes / IP limit with `fundingInfo`.

Funding history is therefore a long-horizon candidate, but exact earliest availability must still be empirically discovered and receipted per symbol.

### Mark-price klines

Endpoint: `GET /fapi/v1/markPriceKlines`

The official endpoint supports `startTime`, `endTime`, and a maximum limit of 1500. V0.1 supports `15m`, `1h`, and `4h` mark-price bars. A mark-price candle becomes usable only after its documented close time has passed.

No fixed retention cap is stated on the endpoint page, so exact earliest availability must be measured rather than assumed.

### Open-interest history

Endpoint: `GET /futures/data/openInterestHist`

The official endpoint supports `startTime`, `endTime`, period values from `5m` through `1d`, and a maximum limit of 500. Binance explicitly documents that **only the latest 1 month is available**.

V0.1 therefore does **not** treat Binance Open Interest as an eight-year backfill source. The project uses a conservative 30-day query window and may accumulate new OI evidence forward from now on.

## Implementation

### Public client

`src/crypto_autopilot/exchanges/binance_usdm_public.py`

Public-only methods:

- trade klines
- mark-price klines
- funding-rate history
- open-interest history

No API key, signing, balances, positions, orders, or execution methods exist in this client.

### Historical pagination and audit

`src/crypto_autopilot/binance_historical.py`

V0.1 provides deterministic forward pagination for:

- trade klines;
- mark-price klines;
- funding history;
- the provider-retained recent OI window.

Trade klines reuse the existing strict candle audit. Mark-price history requires contiguous closed bars. Funding and OI reject conflicting duplicate authority and pagination that fails to advance.

## Symbol mapping

Example:

```text
Pionex: BTC_USDT_PERP
Binance: BTCUSDT
```

This mapping means only that the two symbols refer to a syntactically corresponding USDT perpetual candidate. It does not prove market equivalence, candle equivalence, liquidity equivalence, or strategy-signal equivalence.

## Backtest funding bridge

`to_backtest_funding_points()` can convert Binance funding rows to the existing Backtest Engine `FundingPoint` shape so research simulations can include funding costs.

The original Binance backfill result/receipt must remain attached to the research result. Conversion into a common in-memory shape does not convert provenance.

## R2 direction

A future Binance materialization must use a distinct provider namespace, for example:

```text
market-data/binance_usdm/perp/<symbol>/<interval>/...
```

It must never overwrite or share canonical identity with:

```text
market-data/pionex/perp/...
```

## What this does not prove

This foundation does not yet prove:

- that every target Binance symbol has eight years of data;
- exact earliest Kline, funding, or mark-price timestamps;
- Pionex/Binance strategy-signal equivalence;
- a frozen Binance dataset in R2;
- historical OI beyond Binance's documented latest-one-month window;
- real historical liquidity authority for Pionex;
- live trading safety or profitability.

## Next proof

Run a bounded public Binance acquisition proof with no credentials:

1. select a small overlap set including BTC/ETH/SOL;
2. fetch `15m`/`1h`/`4h` trade klines;
3. fetch funding-rate history;
4. fetch mark-price klines;
5. fetch recent OI only within the documented window;
6. audit timestamps and payloads;
7. freeze provider/source provenance and SHA-256 evidence;
8. only then design the long-horizon Binance-to-R2 backfill and Pionex/Binance equivalence gate.
