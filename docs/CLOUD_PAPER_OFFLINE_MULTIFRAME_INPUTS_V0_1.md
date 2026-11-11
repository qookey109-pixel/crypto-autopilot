# Offline multi-timeframe input preparation V0.1

This prepare-only validator accepts pre-supplied in-memory candle objects. It
issues no provider requests, does not persist input, and cannot authenticate
provider provenance or grant strategy eligibility. It is not connected to the
Cloud Paper runtime or a schedule.

It requires the exact 23 prepared breadth symbols, exactly BTC and ETH reference
symbols, 21 contiguous aligned closed 4H candles for each, and at most five
candidate symbols with exactly 200 contiguous aligned closed 15M candles each.
It rejects missing or extra breadth/reference symbols, stale or future bars,
gaps, non-finite prices, invalid OHLC and windows touching the frozen period.
It reuses the existing breadth and technical indicator calculations and returns
the in-memory reference bars and breadth series for subsequent composition.

These checks demonstrate data-shape behavior only. They do not establish the
live Pionex universe, data-source rights, price semantics, actual freshness at
fetch, TOTAL3 or BTC dominance, complete strategy warmup, provider quota,
account-wide budget, or exchange/holdout permissions. In particular, the fixed
breadth membership remains a prepared candidate, not validated current coverage.
Production and schedule stay disabled until separate reviewed authority and
acceptance. Preserve the current 18-request gate; the V0.3 direct-fetch
estimate is not authority to increase it.
