# Binance Maximum-Available Historical Coverage Discovery V0.1

## Purpose

Discover the real provider-available Binance Vision historical boundary for the frozen 15-market M1A candidate universe before any staged multi-year expansion is authorized.

This phase is **coverage discovery only**. It does not authorize source switching, bulk R2 expansion, strategy replay, or live trading.

## Frozen authority and scope

Candidate authority:

- `research/receipts/2026-08-17-m1a-pionex.json`
- exactly 15 frozen Pionex candidate markets
- Binance symbols are derived from the existing deterministic Pionex -> Binance USD-M mapping

Series:

- Trade Klines `15m`
- Trade Klines `1h`
- Trade Klines `4h`
- Mark Price Klines `1h`

Funding and Open Interest are intentionally out of scope for this discovery and remain separate future authorities.

## Time boundary

The project target is maximum provider-available history capped at eight years.

The discovery does **not** assume that any symbol has eight years of data and does not assume that all symbols begin in 2020.

The effective monthly scan floor is the later of:

1. the project eight-year cap floor; or
2. the Binance Vision V0.1 provider archive floor `2020-01`.

The scan covers all complete UTC months through the previous UTC month. The current incomplete UTC month is handled separately using published daily archives through yesterday UTC.

## Evidence method

### Interior coverage presence

Every symbol / series / month is checked through the official Binance Vision `.CHECKSUM` object.

- valid CHECKSUM -> `AVAILABLE`
- HTTP 404 -> explicit `NO_DATA`
- transient/server/network errors -> retry, then fail closed
- malformed CHECKSUM or filename mismatch -> fail closed

The result preserves every available and missing month and explicitly records missing months inside the observed coverage span.

### Exact boundary audit

For every symbol / series, the first and last available monthly archives are downloaded and audited using the existing Binance Vision ingest path.

The audit requires:

- official CHECKSUM
- exact archive SHA-256
- expected ZIP member
- strict timestamp order
- unique timestamps
- candle or Mark Price continuity checks already enforced by the existing V0.1 ingest code

If a current-month daily archive is published, the latest available daily archive is also downloaded and audited so the latest boundary can extend beyond the last completed monthly archive.

The output records the actual earliest and latest audited candle timestamps, not inferred listing dates.

## Per-symbol result

Each Binance symbol receives:

- per-series first/last available archive period
- per-series missing archive periods inside the observed span
- audited earliest candle timestamp
- audited latest candle timestamp
- common Trade-Kline window across `15m` / `1h` / `4h`
- common strategy-price window across Trade Klines plus Mark Price `1h`

The common windows are conservative intersections. They are intended to define later staged-backfill planning boundaries, not to authorize the backfill by themselves.

## Interpretation boundary

A completed discovery proves only that the coverage boundary was measured according to this frozen protocol.

It does **not** prove:

- exchange listing or delisting dates
- full interior candle-content continuity across every archive
- Pionex/Binance equivalence
- Pionex-native provenance
- long-horizon Funding completeness
- long-horizon Open Interest completeness
- historical liquidity completeness
- historical SState completeness
- strategy-parameter validity
- source-switch authorization
- large-scale R2 backfill authorization
- live trading authorization

No interpolation, provider splicing, Pionex relabeling, R2 writes, private API calls, or order execution occurs in this phase.

## Output

Workflow artifact:

- `artifacts/binance-max-coverage-discovery.json`

Expected top-level state after a successful complete run:

- `execution_status = PASS`
- `coverage_status = COMPLETE`
- `source_switch_authorized = false`
- `large_scale_backfill_authorized = false`

A successful discovery should be frozen in a separate authority receipt before staged multi-year expansion planning begins.
