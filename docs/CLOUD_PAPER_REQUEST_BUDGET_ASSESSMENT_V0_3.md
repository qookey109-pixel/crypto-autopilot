# Cloud Paper market request budget V0.3 — prepared analysis

The [V0.2 estimate](CLOUD_PAPER_REQUEST_BUDGET_ASSESSMENT_V0_2.md) counted 23
fixed Pionex breadth markets but did not explicitly budget separate 4H BTC and
ETH price series. The [breadth membership](../config/market_regime_pionex_breadth_universe_v0_1.json)
excludes BTC and ETH, while the [regime input contract](../config/market_regime_breadth_research_v0_1.json)
requires both close series. V0.2 remains unchanged historical evidence.

Under the **specific uncached direct-fetch design**, one Pionex public Kline
request per symbol and interval, five candidates, and up to five open positions:

| Component | Requests per slot |
| --- | ---: |
| Shared market metadata | 3 |
| Fixed 23-member 4H breadth | 23 |
| BTC and ETH 4H reference series | 2 |
| Five candidate 60M + five candidate 15M series | 10 |
| Up to five position book/trade frames | 10 |
| Total | 48 |

At 96 slots/day this is **4,608/day** and **138,240/30 days** under
the assumptions. The market-bar portion is 25×21 + 10×200 = **2,525**
closed bars per slot. These are conditional design bounds, not measured
provider use, a rate-limit allowance, or a zero-cost claim. Macro-provider
requests, retries, other workloads and shared account use are not included.
The 21-bar minima follow V0.2's code-derived shared indicator requirements;
strategy-specific warmup may be greater.

At minimum, the direct design's three shared requests plus 25 4H series
already require 28 requests before candidate candles or position frames,
above the existing 18-request/run contract. Alternative approaches such as
verified batching, valid source reuse, 60M aggregation or a durable 4H cache
could change the calculation; none is assumed available or authorized.
Any cache needs separate storage, request, freshness and recovery accounting.

The successor [configuration](../config/cloud_paper_market_request_budget_v0_3.json)
is **prepare-only**. It does not authorize a provider, R2 or D1 request, a
source switch, runtime or schedule activation, training, strategy changes,
holdout access, promotion, or real-money trading. It does not claim that
BTC/ETH perpetual prices are economically equivalent to every possible regime
price definition. Source semantics, exact coverage, aligned closed bars,
freshness, TOTAL3, BTC dominance and complete account/provider budgets remain
unverified. Preserve fail-closed behavior until a separate reviewed contract.
