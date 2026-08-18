# Historical Capacity and Backfill V0.1

Updated: 2026-08-18

## Status

Capacity sizing is complete from observed M1B evidence. Long-horizon acquisition has not started.

Formal safety boundary remains **PAPER-ONLY**. No private Pionex API or live trading path is authorized by this document.

## Evidence basis

Authoritative storage receipt:

`research/receipts/2026-08-18-m1b-r2.json`

Observed bounded dataset:

- 15 Pionex perpetual symbols
- 7 complete days
- intervals: `15M`, `60M`, `4H`
- 13,230 rows
- 45 Parquet objects
- 425,161 total Parquet bytes
- Zstandard compression
- SHA-256 verified R2 upload/download
- Parquet decode and exact candle equality verified

Observed interval breakdown from the frozen M1B manifest:

| Interval | Rows | Parquet bytes |
| --- | ---: | ---: |
| `15M` | 10,080 | 260,060 |
| `60M` | 2,520 | 109,263 |
| `4H` | 630 | 55,838 |
| **Total** | **13,230** | **425,161** |

The seven-day files include Parquet/file metadata overhead. Linear scaling is therefore treated as a conservative sizing estimate, especially for annual `60M` / `4H` partitions where long files should amortize fixed overhead better.

## Capacity estimate

Using the measured total payload and linear scaling:

| Universe | Horizon | All three native intervals |
| --- | ---: | ---: |
| 15 markets | 1 year | ~0.0222 GB |
| 15 markets | 8 years | ~0.1774 GB |
| 100 markets | 8 years | ~1.1824 GB |
| 250 markets | 8 years | ~2.9559 GB |

Using only the measured `15M` payload as a canonical-store comparison:

- 250 markets × 8 years × `15M` only: ~1.8080 GB
- 100 markets × 8 years × `15M` only: ~0.7232 GB

The current recommendation is **not** to drop native `60M` / `4H` merely to save storage. The conservative 250-market / 8-year / three-interval estimate is already small enough that preserving native exchange candle semantics has more value than saving roughly 1.15 GB. A future strategy-signal equivalence proof may still authorize deterministic resampling/cached derived intervals.

### Safety multipliers

For the 250-market / 8-year / three-interval estimate:

- measured linear estimate: ~2.956 GB
- 2× planning factor: ~5.912 GB
- 3× planning factor: ~8.868 GB

These factors are capacity-planning headroom, not predictions of actual usage. Actual retained history should be lower because many markets will not have eight full years of native Pionex perpetual history.

## Cloudflare R2 pricing snapshot

Pricing checked on 2026-08-18 against Cloudflare's official R2 pricing documentation.

Standard storage snapshot:

- storage: USD 0.015 / GB-month
- Class A: USD 4.50 / million requests
- Class B: USD 0.36 / million requests
- egress: free
- monthly free tier: 10 GB-month storage, 1 million Class A requests, 10 million Class B requests

Source: `https://developers.cloudflare.com/r2/pricing/`

The project-only 250-market / 8-year candle estimate is below the 10 GB-month Standard storage free-tier allowance even at a 3× capacity factor. Therefore the estimated marginal R2 storage charge for this candle dataset is USD 0/month **if the account's free R2 allowance remains available and is not consumed by other workloads**.

## R2 object and operation budget

Current partition policy:

- `15M`: monthly
- `60M`: annual
- `4H`: annual

Worst-case full 8-year × 250-market object count if every market has complete history:

- `15M`: 250 × 8 × 12 = 24,000 objects
- `60M`: 250 × 8 = 2,000 objects
- `4H`: 250 × 8 = 2,000 objects
- total market-data objects: **28,000**

A minimum write + verified-read pass is approximately:

- ~28,000 Class A `PutObject` operations
- ~28,000 Class B `GetObject` verification operations

Manifest, receipt and checkpoint operations add overhead but remain far below the monthly free-tier operation allowances at this scale. Even a 10× operational safety factor remains below 1 million Class A and 10 million Class B requests.

## Pionex acquisition budget

Official Pionex Kline API facts checked on 2026-08-18:

- route: `GET /api/v1/market/klines`
- weight: 1
- page limit: 1–500, default 100
- intervals include `15M`, `60M`, `4H`
- all `/api/` routes share a 10 requests/second IP limit
- rate-limit violation can return HTTP 429 and a 60-second IP ban; repeated violations can extend the ban

Sources:

- `https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines`
- `https://pionex-doc.gitbook.io/apidocs/restful/general/rate-limit`

For a strict eight-year upper bound using 500 rows/page and 365.25 days/year:

- `15M`: 562 pages/symbol
- `60M`: 141 pages/symbol
- `4H`: 36 pages/symbol
- total: 739 pages/symbol
- 250 full-history symbols: **184,750 Kline pages**

This is an upper design bound, not an expected request count. Actual requests should be lower because listing dates and provider history differ by symbol.

### Backfill pacing

Initial global soft target:

- **3 Kline requests/second**
- stay well below the documented 10 requests/second IP ceiling
- on 429: stop, wait at least 65 seconds plus jitter, then resume conservatively
- exponential backoff for repeated transient failures
- never use aggressive parallelism merely to finish faster

At exactly 3 requests/second, 184,750 requests would require about 17.1 hours of pure pacing time before network latency, retries and job overhead. This is why the backfill must be resumable and sharded instead of one monolithic job.

## Resumable backfill design

### 1. Preserve native provenance

Canonical namespace remains provider-specific:

`market-data/pionex/perp/<SYMBOL>/<INTERVAL>/...`

External proxy history must use a different provider namespace and must never be presented as Pionex-native history.

### 2. Deterministic partition targets

Use the existing object-key contract:

- `15M` finalizes one UTC calendar month at a time
- `60M` finalizes one UTC calendar year at a time
- `4H` finalizes one UTC calendar year at a time

Partial first/last partitions are allowed only when provider availability genuinely begins/ends inside that partition; their requested and actual timestamp boundaries must be recorded.

### 3. Newest-to-oldest acquisition

Continue the already validated backward pagination behavior:

- request newest eligible page
- next `endTime = earliest_time - 1 ms`
- audit strict ordering and uniqueness
- stop only on an explicit provider-history boundary / empty eligible page or the configured eight-year cap

No missing candle is silently interpolated.

### 4. Staging before canonical finalize

A partition must not appear authoritative while incomplete.

Recommended lifecycle:

`PENDING -> ACQUIRING -> STAGED -> VERIFIED -> FINALIZED`

Write incomplete work under a staging/checkpoint namespace. Write the canonical market-data key only after the full partition has passed:

- row/count audit
- timestamp ordering/uniqueness
- gap/alignment audit
- OHLCV validity
- Parquet encode/decode
- R2 SHA-256 verified round trip

### 5. Idempotent resume

Each work item is identified by:

`provider + market_type + symbol + interval + partition`

Before acquisition:

- if a FINALIZED canonical object + receipt already exists and verifies, skip it
- if a STAGED checkpoint exists, resume from its frozen oldest timestamp/page boundary
- if staging is invalid or receipt mismatch occurs, quarantine that work item instead of overwriting a valid finalized object

Retries must not create duplicate canonical partitions.

### 6. Checkpoint contents

Persist at least:

- work-item identity
- state
- source/provider
- requested range
- current oldest/newest acquired timestamp
- rows/pages acquired
- next `endTime`
- attempt count
- last HTTP status/error
- last successful update timestamp
- source run/job identifier

Checkpoint frequency should be bounded (for example every 10 successful pages and on graceful shutdown) so resumability does not create excessive tiny writes.

### 7. Bounded GitHub Actions shards

Do not launch 250 markets in one job.

Initial pilot recommendation:

- 5 symbols per shard
- all three native intervals
- one-year bounded proof first
- `max-parallel: 1` initially
- job timeout around 45 minutes
- persist checkpoints to R2

After successful pilot evidence, increase shard size or concurrency only if 429 rate, retries, data integrity and runner time remain acceptable.

### 8. Historical universe safety

Do not backtest eight years using today's top-250 list as if those markets existed for the whole period.

Before full research use, maintain a historical-universe registry with at least:

- provider symbol
- asset family
- first observed/native-history timestamp
- last observed timestamp / delisting state when applicable
- provenance/source
- whether history is Pionex-native or external proxy

The full backfill may collect current candidate markets, but strategy evaluation must select assets using information available at each historical date.

## Recommended next implementation

Build a bounded **Historical Backfill Pilot** rather than immediately starting 8 years × 250 markets.

Pilot gate:

1. 15 current M1A symbols.
2. One complete year where provider history exists, capped to the requested range.
3. Native `15M`, `60M`, `4H` retained.
4. 3 requests/second soft pacing.
5. R2 staging + resumable checkpoints.
6. Deterministic partition finalization.
7. Restart/resume test intentionally interrupts at least one shard and proves no duplicate/lost rows.
8. All finalized objects receive SHA-256 + Parquet + candle-integrity receipts.
9. No live/private API use.

Only after this pilot passes should the project authorize maximum-available expansion toward the 8-year / ~250-market design target.
