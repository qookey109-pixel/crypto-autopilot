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
