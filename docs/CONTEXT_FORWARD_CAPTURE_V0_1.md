# Context Forward Capture V0.1

Status: **PREPARED / NOT ACTIVE / RESEARCH ONLY**

## Purpose

Context Source Lineage V0.1 selected CoinPaprika Free as the preferred future
source for **forward current snapshots** of market-wide crypto context while
leaving multi-year historical global context blocked.

This V0.1 prepares the deterministic parsing and capture contract needed for a
future separately authorized collector. It does not grant permission to call
the provider, create a workflow, write R2, open the replacement holdout, change
the strategy, execute SHORT, promote a model, create a trade plan, place a
real-money order, or enable live trading.

Authority/config:

- `config/context_forward_capture_v0_1.json`
- source decision: `config/context_source_lineage_v0_1.json`
- parser: `src/crypto_autopilot/providers/context_forward_capture.py`

## Frozen source lineage

The capture config is SHA-256 bound to the exact current bytes of
`config/context_source_lineage_v0_1.json`.

The prepared source remains:

- provider: CoinPaprika;
- plan: Free;
- base URL: `https://api.coinpaprika.com/v1/`;
- `/global` for total crypto market capitalization, BTC dominance, and its
  provider update timestamp;
- `/tickers/eth-ethereum` for same-provider ETH USD market capitalization and
  its provider update timestamp;
- no API key on this prepared Free path;
- no paid fallback.

The official CoinPaprika documentation records `/global.last_updated` as Unix
seconds and ticker `last_updated` as an ISO-8601 timestamp. Both endpoints are
current-snapshot sources, not a canonical multi-year global-history feed.

## Semantic formula

The parser preserves the same-provider formula already frozen by Context Source
Lineage V0.1:

```text
total_market_cap_usd = /global.market_cap_usd
btc_dominance_pct    = /global.bitcoin_dominance_percentage
btc_market_cap_usd   = total_market_cap_usd * btc_dominance_pct / 100
eth_market_cap_usd   = /tickers/eth-ethereum.quotes.USD.market_cap

total3_value = total_market_cap_usd
             - btc_market_cap_usd
             - eth_market_cap_usd
```

`total3_value` is the project's semantic ex-BTC/ETH aggregate. It is not a
claim that a proprietary chart symbol was fetched.

## Snapshot schema

A valid synthetic/prepared snapshot is emitted as:

`context-forward-snapshot-v0.1`

It records:

- provider identity;
- explicit capture timestamp;
- `/global` provider timestamp;
- ETH ticker provider timestamp;
- component timestamp skew;
- age of each provider component at capture time;
- total crypto market cap;
- BTC dominance;
- derived BTC market cap;
- ETH market cap;
- derived `total3_value`;
- exact endpoint identities;
- SHA-256 of each exact raw payload byte sequence;
- `forward_only=true`;
- `historical_backfill_claim=false`;
- `authority=false`.

Raw payload hashes are evidence fingerprints. V0.1 does not authorize raw
payload persistence or redistribution.

## Data-quality boundary

The prepared parser fails closed when any of these conditions occurs:

- either payload is missing, empty, non-UTF-8, malformed JSON, or not an object;
- duplicate JSON object keys are present;
- required numeric fields are missing, non-finite, or non-positive where
  positivity is required;
- BTC dominance is not strictly between 0 and 100;
- ETH ticker identity is not exactly `eth-ethereum` / `ETH`;
- `quotes.USD.market_cap` is missing;
- either provider timestamp is later than the capture timestamp;
- either provider component is more than 900 seconds old;
- the two provider timestamps differ by more than 600 seconds;
- derived `total3_value` is zero, negative, or non-finite.

The 900-second age gate and 600-second component-skew gate are capture-quality
bounds, not trading parameters. Changing them requires a new reviewed version.
No interpolation, backward carry, or forward carry is allowed.

## Why two timestamp gates exist

CoinPaprika documents roughly five-minute updates for the relevant Free current
endpoints. A future capture must not silently combine a fresh global aggregate
with an old ETH market cap or accept stale provider state merely because both
HTTP requests returned 200.

V0.1 therefore preregisters:

- maximum provider age: 15 minutes;
- maximum cross-component provider timestamp skew: 10 minutes.

These values are deliberately frozen before any production forward evidence is
collected so later observations cannot tune the data-quality gate after seeing
results.

## Exact raw-payload lineage

The parser hashes the **raw response bytes**, not a reserialized or normalized
JSON object. Therefore harmless-looking changes in whitespace, field encoding,
or payload bytes remain visible in provenance even when the parsed semantic
values are the same.

JSON duplicate keys are rejected because accepting them would make semantics
dependent on parser-specific last-key-wins behavior.

## Prepared transport boundary

The module exposes an injected-transport shape so the future request order is
explicit:

1. `https://api.coinpaprika.com/v1/global`
2. `https://api.coinpaprika.com/v1/tickers/eth-ethereum`

However the frozen V0.1 config keeps `provider_fetch_authorized=false` and
`provider_request_entrypoint_enabled=false`.

`prepared_collect_context_forward_snapshot(...)` must therefore raise before
calling the injected transport even once. V0.1 intentionally has no default
network transport.

This makes the engineering surface testable without turning preparation into
runtime authority.

## Free-only capacity projection

A future nominal 4H collector would need six captures/day. At exactly two
requests per capture:

```text
6 captures/day * 2 requests * 30 days = 360 requests/month
```

The source-lineage decision records a documented CoinPaprika Free allowance of
20,000 requests/month, so this nominal shape is far below that allowance.

This is capacity planning only. It does not authorize provider execution,
scheduling, retries, or automatic fallback.

## Historical boundary remains unchanged

This work does not solve historical global context.

The following remain true:

- multi-year canonical global market-cap/BTC-dominance history is blocked under
  the current $0 policy;
- no current snapshot may be carried backward to fabricate old context;
- CoinPaprika per-coin history may not be summed from a present-day membership
  list and called canonical global history;
- unofficial TradingView/chart scraping remains rejected as formal lineage;
- Contextual Edge Evaluation V0.1 cannot claim real historical regime uplift
  from fabricated global values.

## Integration boundary

This prepared capture contract may later feed the forward side of Market Regime
/ Altcoin Breadth V0.1 after a separate execution authority exists.

It does not alter:

- `config/strategy_v0_1.json`;
- SState;
- opportunity score;
- risk sizing;
- leverage;
- LONG_ONLY direction;
- provider-equivalence authority;
- replacement holdout state;
- current GitHub schedule inventory.

## Next eligible step

A separately versioned **Context Forward Capture Execution Authority** may later
be reviewed. That authority would need to define, at minimum:

- exact activation time;
- exact schedule or manual-only execution path;
- network transport and timeout behavior;
- failure/no-retry behavior;
- immutable evidence destination, if storage is desired;
- free-tier headroom policy;
- health/observability classification;
- explicit confirmation that historical backfill remains false.

Until such authority is merged, V0.1 remains preparation only.

## Authority boundary

All provider-fetch, production R2 read/write, historical backfill, workflow
schedule, holdout, replacement-holdout tuning, strategy/risk/leverage change,
SHORT execution, model promotion, trade-plan, real-money-order, and live-trading
authorities remain false.
