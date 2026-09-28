# Global Market Context Source Decision Map V0.1

Status: **PROPOSAL_ONLY / NO_SOURCE_AUTHORIZED / NO_NETWORK_CAPTURE**

Evidence checked: 2026-09-28 against Repository main `2bded2b8ba6d42cb89a33d2dafd3160cb8687a76` and the current research and Cloud Paper contracts.

This is a planning record only. It does not grant provider access, change the Pionex candle source, change regime rules, authorize API credentials, add a schedule, or enable Cloud Paper.

## Decision to make

The Cloud Paper loop requires causal global context for `TOTAL3`, `BTC_DOMINANCE`, and `ALIGNED_BREADTH`. Pionex public market endpoints provide exchange and contract data; a Pionex API key does not add global market-cap context. The existing External Market Context V0.1 authorizes only ingestion of caller-supplied/prefetched evidence and explicitly prohibits network capture.

A future source must provide evidence with a stable source identity, its own observation/availability timestamps, an explicit common decision timestamp, and enough provenance to reject stale, incomplete, mixed-window, or mismatched data.

## Existing project definitions and Pionex data fit

The project has already frozen the research semantics in `config/market_regime_breadth_research_v0_1.json` and `docs/MARKET_REGIME_BREADTH_RESEARCH_V0_1.md`:

- `TOTAL3` means aggregate crypto market capitalization excluding BTC and ETH.
- BTC dominance is BTC market capitalization divided by total crypto market capitalization, in percent.
- Breadth is equal-weight across a fixed, exactly aligned crypto market universe, excluding BTC and ETH, with at least 20 markets. The supported intervals are 4H and 1D; missing bars fail closed. The output measures above-EMA20 and positive five-bar momentum ratios.
- This contract is research-only: it authorizes no provider fetch, R2 access, production regime gate, or trading change.

The existing Pionex validation dataset does not itself provide the required crypto breadth universe through its `BREADTH_BACKGROUND` profile: it contains 68 symbols, with **0 crypto symbols** (51 equity-linked tokens, 15 ETF/fund-linked tokens, 2 precious-metal references). A deterministic candidate set is now prepared in `config/market_regime_pionex_breadth_universe_v0_1.json`: 23 crypto-only markets from the existing curated 30-asset pool, intersected with the Pionex 4H/1D history-profile assignments. This exceeds the 20-market minimum without inspecting returns or provider payloads. It is only a membership proposal: partition completeness, exact aligned grids, freshness and current availability remain unverified. The historical materialization is cutoff-bound; R2 reads require separate authority, and missing members must make breadth unavailable rather than shrink the set.

## Candidate reviewed: CoinMarketCap Global Metrics

The official API docs show that `/v1/global-metrics/quotes/latest` is available on the Basic plan, returns `btc_dominance` and `altcoin_market_cap`, and updates every five minutes. The official pricing page lists Basic as free with 15,000 monthly credits and a 50 requests/minute limit. For a production integration, the reviewed pricing/docs distinguish the keyed Basic plan from the keyless public API, which is described as a prototype path. A production key would be a CoinMarketCap key stored only in the approved GitHub secret boundary; a Pionex key is unrelated.

- [Global Metrics endpoint and Basic-plan availability](https://coinmarketcap.com/api/documentation/pro-api-reference/global-metrics)
- [CoinMarketCap Basic pricing, rate and monthly credits](https://coinmarketcap.com/api/pricing/)
- [CoinMarketCap Keyless Public API guidance](https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api)
- [CoinMarketCap Commercial Terms](https://pro.coinmarketcap.com/user-agreement-commercial/)

The project’s TOTAL3 semantic (ex-BTC/ETH) is now known. The API documentation exposes a field named `altcoin_market_cap`, but the reviewed endpoint field documentation does not provide enough methodology to certify that field as exactly the project metric. Do not mark it equivalent without source-methodology evidence and an authorized sample. The pricing/terms pages also require an attribution link and restrict how data is stored and presented; applicability to this project's R2 evidence retention and public Pages projection must be reviewed before use.

## Metric, breadth and budget fit

| Requirement | Current evidence | Finding |
| --- | --- | --- |
| BTC dominance | Global Metrics response has `btc_dominance`; endpoint updates every five minutes | Candidate field exists; source timestamp, causal alignment and freshness against the decision timestamp still need validation. |
| TOTAL3 | Project semantics are ex-BTC/ETH; API response has `altcoin_market_cap` | Internal definition is frozen; exact provider methodology equivalence remains unverified. |
| Aligned breadth | Existing rule is fixed, equal-weight, 4H/1D, at least 20 crypto markets with an exact common bar grid | Must be derived from Pionex-native candles. Candidate membership has been prepared at 23 markets (see `config/market_regime_pionex_breadth_universe_v0_1.json`), but partition completeness, exact aligned grids, freshness and update/request budget remain unverified. Missing members must fail closed; do not shrink the set after reading coverage. A second CMC listings call is not inherently required by this breadth rule. |
| CMC call budget | One global-metrics call per 15-minute Cloud Paper slot would be 96/day, at most 2,976 per 31-day month | Within the published 15,000 monthly Basic credits in isolation; shared-account CMC usage is unknown. This adds one request per run (18→19; 1,728→1,824/day) before any separate Pionex breadth refresh requests. |
| Total project budget | Current Cloud Paper V0.1 ceiling is 18 provider calls/run and 1,728/day; breadth capture cadence is not budgeted | The frozen ceiling cannot be silently changed. A successor budget must include CMC calls, Pionex breadth refreshes, retries (currently zero), all writers and account-wide headroom while retaining the 0 USD hard stop. |
| License and storage | CMC pricing advertises free Basic with commercial-use terms; commercial terms require attribution and limit redistribution/storage | Exact fit for scheduled capture, immutable R2 retention, internal derived use and public Pages display remains unapproved; no paid tier is allowed. |

The 2,976/month calculation is a quota comparison, not evidence that the project account has that capacity available. No account usage or API key was inspected. Do not include these calls under Pionex allowances.

## Required checks before any source authority

1. Confirm the provider's exact `altcoin_market_cap` methodology against the project's ex-BTC/ETH definition; preserve provider-native timestamps and reject mismatched/stale values.
2. Verify the prepared exact 23-market membership against allowlisted Pionex partition receipts under a separate bounded R2-read authority. Require complete contiguous 4H and/or 1D bars on one exact grid and current availability; do not drop any member to force a PASS. Do not use the existing 68-market `BREADTH_BACKGROUND` profile as crypto breadth.
3. Set a separate breadth refresh/request plan and successor total project budget; prove current account-wide R2, D1 and provider headroom before any external operation.
4. Review the exact CMC Basic terms for scheduled use, internal derived calculations, R2 evidence retention and public display; implement required attribution if applicable. A free plan is not proof of account-wide zero cost by itself.
5. Only after the exact source/budget authority and secret-free acceptance criteria are versioned and merged may a bounded sample be requested. Until then, no endpoint call, key request, R2 read/write, schedule or source switch is authorized.
6. Synthetic CI must cover missing fields, stale/misaligned timestamps, incomplete breadth, provider errors, budget exhaustion and zero-trade fail-closed behavior. Synthetic fixtures are not provider or strategy evidence.

## Current consequence

Current production behavior remains `REGIME_UNAVAILABLE` and `NO_TRADE`. The strategy registry is empty and Core100 quality is `REJECT`; a future market-context PASS would not authorize a position, strategy registration, threshold change, promotion, holdout access, or live trading.

No provider API endpoint was called for this decision map. No API key was requested or stored.
