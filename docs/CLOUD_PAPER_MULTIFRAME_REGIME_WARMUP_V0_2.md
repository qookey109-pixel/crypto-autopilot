# Full 4H breadth warmup — prepare-only successor

V0.1 accepted 21 closed 4H bars per breadth market and exposed only two
breadth points with EMA20 ready. The existing regime calculator requires
21 complete observations for its 20-bar lookback. A self-contained window
therefore needs **40** contiguous bars for each of the 23 breadth markets:
the first ready EMA20 is bar 20, leaving 21 ready points through bar 40.

The offline V0.2 validator checks the full 40-bar window and returns the
last 21 ready breadth points aligned with 21 validated BTC and ETH 4H bars.
It reuses V0.1's 15M candidate and reference checks. TOTAL3 and BTC-dominance
observations in the integration test are synthetic; the validator neither
produces nor authenticates those external fields.

The prepared [V0.4 budget](../config/cloud_paper_market_request_budget_v0_4.json)
corrects the per-slot bar count from 2,525 to **2,962** under the same
direct-fetch assumptions: 23×40 + 2×21 + 5×200 + 5×200. The number of
requests remains 48 only if every per-symbol window fits one response; that
is a design assumption, not proof of a production quota or source coverage.
Macro calls, retries, other writers and all actual account costs remain
outside that number. The prior V0.3 file remains unchanged as historical
evidence. Strategy-specific warmup may still exceed these minima.

These components run entirely on supplied in-memory fixtures. They do not
fetch or authenticate market data, alter strategy eligibility, call R2 or D1,
open holdout, change source, promote a model, or authorize runtime or a
schedule. Current provider and shared-budget gates remain closed.

## Pionex documented request constraints — 2026-11-11

The official [Klines documentation](https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines) specifies one mandatory symbol and interval per request, includes 15M, 60M and 4H intervals, and documents a maximum limit of 500 bars (default 100). Thus the 40- and 200-bar windows fit the documented per-response limit when explicitly requested, but the documented endpoint does not establish multi-symbol batching. This does not verify availability of any perpetual symbol, response freshness, gaps, current inclusion, live behavior or exact semantics; actual responses remain untested. The 48-call estimate remains conditional and above the existing 18-call per-run limit.

The provider [rate-limit documentation](https://pionex-doc.gitbook.io/apidocs/restful/general/rate-limit) states a shared IP limit of 10 weighted requests per second and that exceeding limits can result in a 429 and temporary ban. The Klines endpoint is documented with weight 1, while other endpoints may have different weights. The IP limit is not a daily allocation, a guarantee for a shared GitHub runner IP, or evidence that the project's own 18-call limit may be exceeded. Any future execution must account for concurrent workloads and fail closed on limits and incomplete data.

Possible request reduction by reusing previously validated closed 4H windows is a design candidate only: it requires separately verified freshness, integrity, restart behavior, missed-slot handling, budgets and authorization. No cache, provider request, new schedule, additional budget, or source switch is authorized by this note.
