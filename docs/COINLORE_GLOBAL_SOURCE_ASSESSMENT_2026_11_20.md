# CoinLore global market data — source assessment

Observed 2026-11-20 from the provider's documentation and methodology.
Repository evidence basis: parent main `a2a282281f08e262e0b2e862a3c874005601b0e2`.
This assessment makes no API request and grants no source, storage, runtime or
schedule authority.

## Candidate fields

CoinLore documents a free public global endpoint without registration or an
API key, recommending approximately one request per second for fair usage.
The documented response includes `total_mcap` in USD and BTC and ETH market
dominance percentages `btc_d` and `eth_d`. The documented global response
does not list an observation or update timestamp. The provider says it may
temporarily reference previously validated prices when current data is
unreliable, so response receipt time cannot establish freshness.

The documented percentage strings in the example use two decimal places.
Total market cap multiplied by one minus the sum of BTC and ETH dominance
fractions is only a candidate approximation for the project's ex-BTC/ETH
TOTAL3 definition. Rounding error, methodology, universe membership and
cross-field time consistency must be characterized before treating it as
equivalent. Do not silently use that approximation as the existing TOTAL3.

Sources: [CoinLore API documentation](https://www.coinlore.com/cryptocurrency-data-api),
[CoinLore methodology](https://www.coinlore.com/methodology).

## Status and unresolved evidence

- BTC dominance: documented candidate, timestamp and freshness unverified.
- TOTAL3: no direct field identified; derived approximation and required
  precision are unverified.
- Historical global snapshots needed for the existing regime lookback are
  not established by the reviewed global endpoint.
- Explicit permission for retained decision inputs, derived data and public
  projection is unverified. Provider terms and attribution must be reviewed.
- Provider quota shared with other uses, uptime, latency, symbol coverage and
  exact runtime cost are unverified.
- The existing 18-request limit and separate Pionex provenance rules remain
  applicable. No provider API request was made as part of this assessment.

Classification: `CANDIDATE_NOT_APPROVED`. Unknown freshness, completeness,
license or budget means the field remains unavailable to the formal cycle.
