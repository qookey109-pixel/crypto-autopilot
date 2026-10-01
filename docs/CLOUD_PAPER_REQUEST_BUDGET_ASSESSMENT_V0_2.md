# Cloud Paper multi-timeframe request budget assessment V0.2

Basis: GitHub `main=3b58fce4a27d0c65fa17b011fea4946cd20077ee` (2026-10-01).

This is a planning assessment and inactive requirement envelope. It does not authorize provider, R2, or D1 access; runtime activation; strategy qualification; or scheduling. The machine-readable proposal is `config/cloud_paper_market_request_budget_v0_2.json`.

## Request arithmetic

The existing strategy configuration names 4H market context, 60M setup, and 15M entry. The market-regime research contract requires a fixed 23-market breadth set. The current market adapter captures only 60M candles for up to five candidates. The [Pionex Kline documentation](https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines) lists the required intervals and one request weight per Kline request; the repository has not verified live capture completeness, aggregate quota, or rate-limit capacity. Batch Kline support is unverified, so the estimate assumes one request per symbol and interval.

For direct per-symbol candle requests, the upper-bound design is:

| Input | Calls per slot |
|---|---:|
| Shared symbols, tickers, and book tickers | 3 |
| Fixed 23-market 4H breadth | 23 |
| Up to five 60M candidates | 5 |
| Up to five 15M candidates | 5 |
| **Total** | **36** |

At 96 nominal slots/day with no retries or backfill, that is 3,456 calls/day and 103,680 calls per rolling 30 days. The Kline portion contributes at most 33 weight units/slot, 3,168/day, and 95,040 per rolling 30 days under the one-request-per-symbol assumption. Weights for the three shared endpoints, account allowance, and observed shared usage remain unknown. These are arithmetic design bounds, not provider allowances or expected observed usage. The current V0.1 Cloud Paper budget permits 18 requests/run and 1,728/day, so the proposal does not fit it. The active guard must continue to block any request beyond its current limit.

## Freshness and caching

The current schedule runs at minutes 7, 22, 37, and 52, with a maximum start delay of 10 minutes. A 15M closed bar can already be about seven minutes old at nominal start; a delayed start can exceed a proposed 15-minute input-age limit. That limit is a design proposal, not current authority. If adopted, such input must fail closed, and the schedule cannot be treated as guaranteed to produce a new entry on every slot. The approved maximum input age must be derived from strategy needs and explicit authority.

Reusing 4H breadth across separate GitHub-hosted runs requires durable state; in-memory cache ends with the run. A durable cache would add object/query reads and writes, retention, concurrency, recovery, and freshness costs. No cache path is authorized or included in the 36-call envelope. Hashes identify evidence but cannot reconstruct raw data that was discarded.

## Required evidence before any successor can execute

1. Verify required warmup counts for every timeframe from the actual strategy and indicator implementation.
2. Establish fixed breadth membership, per-symbol coverage, closed-bar alignment, and missing-member behavior.
3. Obtain authoritative provider allowance and rate-limit-capacity evidence, plus shared usage from all provider workflows. Public endpoint documentation alone does not establish these.
4. Resolve schedule-to-15M freshness, including delayed starts, without admitting stale candles; record and authorize the chosen maximum age.
5. Compare no-cache requests with a separately costed durable 4H cache. Include cache storage, reads, writes, recovery, retries, and other writers in the shared 0 USD budget.
6. Resolve TOTAL3/BTC-dominance semantics, permitted source and retention terms. Do not relabel exchange data or scrape around access restrictions.
7. Keep synthetic validation in GitHub CI only. No live provider access, R2/D1 access, migration, or schedule dispatch is part of this assessment.

Until these items are evidenced under a reviewed successor authority, Cloud Paper remains inactive. The request envelope is a planning bound and not a change to V0.1's 18-request guard.
