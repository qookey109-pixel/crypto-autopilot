# Global Market Context Source Decision Map V0.1

Status: **PROPOSAL_ONLY / NO_SOURCE_AUTHORIZED / NO_NETWORK_CAPTURE**

Evidence checked: 2026-09-28 against Repository main `77138c1b1ce7c4b99555c6c5f35eaf66dd82c26a` and the current Cloud Paper V0.1 contract.

This is a planning record only. It does not grant provider access, change the Pionex candle source, change regime rules, authorize API credentials, add a schedule, or enable Cloud Paper.

## Decision to make

The Cloud Paper loop requires causal global context for `TOTAL3`, `BTC_DOMINANCE`, and `ALIGNED_BREADTH`. Pionex public market endpoints provide exchange and contract data; a Pionex API key does not add global market-cap context. The existing External Market Context V0.1 authorizes only ingestion of caller-supplied/prefetched evidence and explicitly prohibits network capture.

A future source must provide evidence with a stable source identity, its own observation/availability timestamps, an explicit common decision timestamp, and enough provenance to reject stale, incomplete, mixed-window, or mismatched data.

## Candidate reviewed: CoinMarketCap Keyless Public API

Official documentation currently lists `/v1/global-metrics/quotes/latest` on the keyless `/public-api` path. The sample response includes `btc_dominance`, `eth_dominance`, `total_market_cap`, and `altcoin_market_cap`; the endpoint documents a five-minute update interval. The Keyless API docs say no account/key is required for supported endpoints, but describe keyless access as a prototype path, use an IP-shared rate pool, publish no numeric keyless request ceiling on the page reviewed, and point production users toward a free API key for higher limits/full catalog.

- [CoinMarketCap Global Metrics endpoint](https://coinmarketcap.com/api/documentation/pro-api-reference/global-metrics)
- [CoinMarketCap Keyless Public API](https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api)
- [CoinMarketCap API plans and terms summary](https://coinmarketcap.com/api/pricing/)

This makes CMC a candidate for a bounded evaluation, not an approved production dependency. The public documentation reviewed here does not establish that keyless use permits this project's scheduled production capture, persisted derived evidence, or public Pages projections under the exact applicable terms. The numeric shared-IP rate limit and service guarantee also remain unknown.

## Metric and budget fit

| Requirement | Candidate evidence | Current finding |
| --- | --- | --- |
| BTC dominance | `btc_dominance` on global metrics response | Field exists; field timestamp, causal alignment, and acceptable freshness must be verified from an authorized sample. |
| TOTAL3 | `altcoin_market_cap` and global market-cap fields | **Not equivalent by assumption.** Confirm the frozen project definition, exclusions, units, and provider methodology before mapping it. |
| Aligned breadth | Potentially derive from a listings/quotes endpoint plus a declared asset set and common interval | **Not established.** The global metrics response alone does not provide per-asset breadth. Endpoint fields, timestamp alignment, asset coverage, exclusions, and a minimum valid denominator need a versioned definition. |
| Request ceiling | One global-metrics request; breadth may need a second listings/quotes request | Two requests per 15-minute slot would raise Cloud Paper V0.1 from 18 to 20 requests/run and from 1,728 to 1,920 requests/UTC day (96 slots). This exceeds the frozen V0.1 ceilings. |
| Cost and license | Keyless route is described as no-key; the plan page separately describes free keyed plans | No production entitlement, public display/storage permission, numeric keyless cap, or account-wide cost/headroom proof is established by this review. |

Do not fold these requests into the Pionex allowance or quietly increase the contract ceiling. A replacement contract must account for total account-wide usage, all calls and retries (currently zero retries), daily/monthly reservations, and the 0 USD hard stop.

## Required checks before any source authority

1. Freeze the precise project definitions for TOTAL3 and aligned breadth, including asset universe, exclusions, interval, timestamp tolerance, minimum coverage, and behavior when coverage is incomplete.
2. Review the exact provider terms for automated scheduled use, retained raw/derived fields, artifact storage, and public dashboard display. Confirm a published request limit suitable for 96 daily cycles or select a separately authorized free plan with measured account-wide headroom.
3. Compare an authorized, secret-free sample against those definitions. Preserve provider-native identity and source timestamps. If any field cannot be aligned, emit `REGIME_UNAVAILABLE` and stop that candidate; do not synthesize or substitute.
4. If requests exceed current limits, prepare a new versioned budget/loop contract and receipt. Do not mutate the V0.1 frozen contract or its evidence.
5. Merge a source-specific versioned authority and receipt to protected main before any provider request. Until then, keep network capture closed, Cloud Paper activation disabled, holdout closed, and source-switch authorization false.
6. After implementation, synthetic CI must cover missing fields, stale/misaligned timestamps, partial breadth coverage, rate limiting, and zero-trade fail-closed behavior. Synthetic fixtures are not provider or strategy evidence.

## Current consequence

Current production behavior remains `REGIME_UNAVAILABLE` and `NO_TRADE`. The strategy registry is empty and Core100 quality is `REJECT`; a future market-context PASS would not authorize a position, strategy registration, threshold change, promotion, holdout access, or live trading.

No provider API endpoint was called for this decision map. No API key was requested or stored.
