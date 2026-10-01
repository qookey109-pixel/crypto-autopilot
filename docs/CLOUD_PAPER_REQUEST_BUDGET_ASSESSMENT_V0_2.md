# Cloud Paper multi-timeframe request budget assessment V0.2

Basis: GitHub main=3785314f832d0093b4553b6b94456c2e60943f08 (2026-10-01).

This is a planning assessment and inactive requirement envelope. It does not authorize provider, R2, or D1 access; runtime activation; strategy qualification; or scheduling. The machine-readable proposal is config/cloud_paper_market_request_budget_v0_2.json.

## Request arithmetic

The existing strategy configuration names 4H market context, 60M setup, and 15M entry. The market-regime research contract requires a fixed 23-market breadth set. The current market adapter captures only 60M candles for up to five candidates. The Pionex Kline documentation (https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines) lists the required intervals, up to 500 klines per response, and one request weight per Kline request; the repository has not verified live capture completeness, aggregate quota, or rate-limit capacity. Batch Kline support is unverified, so the estimate assumes one request per symbol and interval.

For direct per-symbol candle requests, the upper-bound design is:

| Input | Calls per slot |
|---|---:|
| Shared symbols, tickers, and book tickers | 3 |
| Fixed 23-market 4H breadth | 23 |
| Up to five 60M candidates | 5 |
| Up to five 15M candidates | 5 |
| **Total** | **36** |

At 96 nominal slots/day with no retries or backfill, that is 3,456 calls/day and 103,680 calls per rolling 30 days. The Kline portion contributes at most 33 weight units/slot, 3,168/day, and 95,040 per rolling 30 days under the one-request-per-symbol assumption. Weights for the three shared endpoints, account allowance, and observed shared usage remain unknown. These are arithmetic design bounds, not provider allowances or expected observed usage. The current V0.1 Cloud Paper budget permits 18 requests/run and 1,728/day, so the proposal does not fit it. The active guard must continue to block any request beyond its current limit. A structural floor is even more restrictive: the three shared requests plus 23 fixed-breadth Klines already require 26 requests/slot before any 60M or 15M candidate Klines. Therefore reducing the candidate limit alone cannot make this direct-source design fit the existing 18-request/run guard. The viable paths are a separately verified and permitted aggregate breadth source, a newly reviewed breadth/cadence contract, or authoritative evidence for a different bounded design; simply raising the numeric ceiling is not evidence of FREE-ONLY feasibility.

## Code-derived warmup minima

The current implementation yields these mathematical lower bounds for complete aligned, closed-candle input:

| Input | Minimum bars | Derivation |
|---|---:|---|
| 4H breadth/regime per market | 21 | The regime uses a 20-bar return lookback (current index 20); breadth EMA20 is ready by then. |
| 60M candidate technicals | 200 | Full ready_v0_2 includes EMA200; the first full snapshot is at index 199. |
| 15M candidate technicals | 200 | Same full technical feature set and EMA200 dependency. |

Market structure's default trailing 20-bar range also needs the current bar plus 20 preceding bars, or 21. Under the stated 23 breadth members and five candidates per candidate timeframe, the resulting lower-bound payload is 2,483 closed candles/slot (23×21 + 5×200 + 5×200). The documented one-request limit of up to 500 can fit each of these per-symbol windows in one request. This only shows the configured windows fit the documented endpoint limit; it does not establish endpoint availability, batch behavior, provider quota, or all strategy-specific dependencies. Additional strategy-family requirements beyond the shared router gate remain unverified.

### Strategy-family input boundary

The current research-only router has six families: trend following, breakout, momentum, mean reversion, high-volatility trend, and low-volatility range. Every routed candidate is gated on an eligible opportunity, a full `TechnicalSnapshot.ready_v0_2`, and a ready, timestamp-aligned market regime. That technical snapshot includes the full shared indicator set, including EMA200, so 200 continuous closed bars is a code-derived lower bound for the current router input at each candidate timeframe. Families that call market-structure matching also need the aligned structure snapshot; its default previous-range inputs require 20 prior bars plus the current bar (21 total). This is consistent with, but does not prove more than, the minima above.

This routing contract is research compatibility only. It does not define the signal-generation implementation, exact entry/exit history window, or paper qualification requirements for a future strategy. The production registry is currently empty, so there is no qualified implementation to inspect for those additional requirements. Do not treat 200 bars as a universal strategy guarantee or use the router's research match as execution eligibility. A future qualified strategy must declare its own per-timeframe inputs, warmup, alignment and staleness requirements, and pass them through a versioned validation receipt before any successor execution authority is considered.

## Freshness and caching

The current schedule runs at minutes 7, 22, 37, and 52, with a maximum start delay of 10 minutes. A 15M closed bar can already be about seven minutes old at nominal start; a delayed start can exceed a proposed 15-minute input-age limit. That limit is a design proposal, not current authority. If adopted, such input must fail closed, and the schedule cannot be treated as guaranteed to produce a new entry on every slot. The approved maximum input age must be derived from strategy needs and explicit authority.

Reusing 4H breadth across separate GitHub-hosted runs requires durable state; in-memory cache ends with the run. A durable cache would add object/query reads and writes, retention, concurrency, recovery, and freshness costs. No cache path is authorized or included in the 36-call envelope. Hashes identify evidence but cannot reconstruct raw data that was discarded.

## Required evidence before any successor can execute

1. For any future qualified implementation, declare and validate per-timeframe inputs, warmup, alignment, and staleness; the current router's shared minima do not certify strategy-specific requirements.
2. Establish fixed breadth membership, per-symbol coverage, closed-bar alignment, and missing-member behavior.
3. Obtain authoritative provider allowance and rate-limit-capacity evidence, plus shared usage from all provider workflows. Public endpoint documentation alone does not establish these.
4. Resolve schedule-to-15M freshness, including delayed starts, without admitting stale candles; record and authorize the chosen maximum age.
5. Compare no-cache requests with a separately costed durable 4H cache. Include cache storage, reads, writes, recovery, retries, and other writers in the shared 0 USD budget.
6. Resolve TOTAL3/BTC-dominance semantics, permitted source and retention terms. Do not relabel exchange data or scrape around access restrictions.
7. Keep synthetic validation in GitHub CI only. No live provider access, R2/D1 access, migration, or schedule dispatch is part of this assessment.

Until these items are evidenced under a reviewed successor authority, Cloud Paper remains inactive. The request envelope is a planning bound and not a change to V0.1's 18-request guard.

## Published Pionex rate limit is distinct from project request budget

Pionex's [official rate-limit documentation](https://pionex-doc.gitbook.io/apidocs/restful/general/rate-limit) documents at most 10 requests per second per IP across endpoints. This fills the previously unknown instantaneous-rate field only. It does not publish an aggregate daily/monthly request allowance on that page, and it does not establish free-tier usage, complete account capacity, or zero-cost operation. The proposed 36 calls/slot could be paced below that instantaneous ceiling in principle, but remains blocked by the current 18/run project contract and unresolved shared usage, allowance, data completeness, and storage-cost evidence. No provider request or budget change is authorized by this clarification.
