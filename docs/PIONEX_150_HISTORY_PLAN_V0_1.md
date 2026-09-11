# Pionex 150+ Historical Acquisition Plan V0.1

Status: **PREPARED — NOT EXECUTION AUTHORITY**

## Purpose

Turn two reviewed future reports into one deterministic historical-acquisition capacity plan:

1. the Pionex 150+ research-universe snapshot report; and
2. the Pionex Historical Reach V0.3 report.

This stage does not call Pionex, read/write R2, access the replacement holdout, train models, or trade.

## Inputs

The universe report must contain at least 150 unique selected markets and preserve one of three history profiles per market:

- `FULL_INTRADAY` → `15M / 60M / 4H / 1D / 1W`
- `MULTISCALE_RESEARCH` → `60M / 4H / 1D / 1W`
- `BREADTH_BACKGROUND` → `1D / 1W`

The reach report must be a PASS for `BTC_USDT_PERP` and contain exact evidence for all five required native intervals.

## Critical reach interpretation

BTC reach is **provider reference evidence only**. It does not prove that another selected market existed for the same period.

A newer meme, tokenized equity, ETF/fund, metal, or crypto perpetual may have a much later listing date. Therefore each market/interval materialization must independently prove its own earliest available boundary.

The planner never copies BTC's earliest timestamp onto another market.

## Capacity contract

For each selected market/interval:

- provider page limit: 500 rows;
- documented maximum records: 10,000;
- maximum data pages: 20;
- one optional boundary probe;
- request upper bound: 21 requests.

Therefore:

- `FULL_INTRADAY`: 5 interval jobs → at most 105 requests/market;
- `MULTISCALE_RESEARCH`: 4 interval jobs → at most 84 requests/market;
- `BREADTH_BACKGROUND`: 2 interval jobs → at most 42 requests/market.

The final total is calculated from the actual selected-universe profile counts. The planner does not force the final universe to exactly 150 markets; the selector may retain more than 150 when valid meme or alternative-asset matches extend the union.

For a representative 150-market fixture containing 30 FULL_INTRADAY, 80 MULTISCALE_RESEARCH and 40 BREADTH_BACKGROUND markets, the deterministic upper bound is 550 market/interval jobs and 11,550 requests. This is a capacity example, not an execution authorization or a claim about the final live profile counts.

## 1Y handling

Pionex does not expose a provider-native `1Y` K-line. `1Y` remains a later derived timeframe from validated `1D` evidence. This planner does not authorize yearly aggregation.

## Failure behavior

The plan fails closed when:

- either input report is not PASS;
- the universe contains fewer than 150 markets;
- symbols are duplicated or a history profile is unknown;
- the reach report does not cover exactly `15M / 60M / 4H / 1D / 1W`;
- a reach interval is not continuity-verified;
- a reach record count is outside 1–10,000;
- an input report indicates R2 or holdout access that violates this prepared planning boundary.

## Explicit non-authority

This stage performs and authorizes no:

- public or private Pionex request;
- R2 read/write;
- historical materialization;
- holdout access;
- model training;
- formal backtest admission;
- source switching;
- strategy change;
- trade plan;
- real-money order;
- live trading.

A later versioned execution authority must bind the actual reviewed universe report, actual reviewed reach report, exact request/storage budget, materialization namespace, retry behavior, and rollback/failure policy before 150+ history acquisition begins.

Config SHA-256: `44ac6dc1d6947e485e6f2aa6bc14bfaf799c8c14b3f859ad813eaf665704e59b`
