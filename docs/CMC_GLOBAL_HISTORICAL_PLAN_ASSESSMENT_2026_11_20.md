# CoinMarketCap global historical plan conflict

Documentation reviewed on 2026-11-20. Evidence basis parent main
`1266dd3dc1c1c8fdcacc4cee535866138bd31ca8`. This is an assessment only; no API request,
account registration, payment, source switch or execution authority is added.

The official [global metrics endpoint reference](https://coinmarketcap.com/api/documentation/pro-api-reference/global-metrics/)
lists Basic for historical quotes, with one month of intraday history.
Its sample includes timestamped total market cap and BTC/ETH dominance.
The provider's [historical data guide](https://coinmarketcap.com/api/resources/cmc-api-historical-data-whats-available-how-far-back-and-how-to-access-it/)
instead says historical global metrics start at Builder. The
[pricing page](https://coinmarketcap.com/api/pricing/) displays Basic as free
and Builder as USD 29/month. Actual Basic eligibility is therefore
`UNVERIFIED_DOCUMENTATION_CONFLICT`, not a confirmed free feature.

If it is available, 4H-aligned timestamps, publication/availability times,
actual coverage, request credits, shared use and semantics of an ex-BTC/ETH
derived market cap still need verification. Research inputs require more than
the presence of a field or a response timestamp.

The pricing comparison states Basic includes commercial use, while the earlier
[decision map](GLOBAL_MARKET_CONTEXT_SOURCE_DECISION_V0_1.md) records a
different legal interpretation from an older terms page. The linked older
terms URL currently renders a generic product page in the documentation
reader. Applicable terms, effective date, retention, derived values, and
public display permission remain `UNVERIFIED`. The old decision and its
historical evidence are preserved.

Keep this source `NOT_APPROVED`. Resolving the conflicting documentation,
license and provider quota requires a separately scoped review before any
runtime usage or external API request. The zero-dollar policy remains binding.
