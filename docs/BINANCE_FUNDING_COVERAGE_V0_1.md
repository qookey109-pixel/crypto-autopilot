# Binance Funding Coverage Discovery V0.1

## Purpose

Discover the maximum observed Binance Vision monthly Funding Rate archive span for the frozen 15-market research universe without assuming Funding availability begins when Trade Klines begin.

This phase is read-only. It does not materialize Funding to R2 and does not authorize backtests or source substitution.

## Authorities

- Candidate universe: `research/receipts/2026-08-17-m1a-pionex.json`
- Funding source proof: `research/receipts/2026-08-18-binance-funding-source-proof.json`
- Protocol: `config/binance_funding_coverage_v0_1.json`

The source proof establishes the monthly Funding archive path/schema/checksum contract and freezes a **10 ms default cadence-jitter tolerance for its Jan-2024 BTC/ETH/SOL proof scope**. It does not establish the 15-symbol long-horizon coverage span.

## Scan scope

The scan starts only from the project history cap floor:

- project cap: 8 years;
- provider onset assumption: **none**;
- source: Binance Vision USD-M monthly `fundingRate`;
- symbols: frozen 15-market M1A universe mapped to Binance USD-M symbols;
- current incomplete month: deferred.

At execution time the runner computes the exact floor and last complete month from UTC time. This prevents the Repository from hard-coding 2020 or reusing Trade-Kline onset as Funding onset.

## Interior scan

For each symbol/month the runner checks the official paired `.CHECKSUM` path:

- existing and valid checksum filename -> `AVAILABLE`;
- HTTP 404 -> `NO_DATA`;
- other failures -> execution failure.

Every expected symbol/month receives exactly one explicit status.

The scan identifies:

- first observed available month;
- last observed available month;
- NO_DATA before onset;
- any missing month inside the observed span.

A pre-onset `NO_DATA` is not treated as an internal gap.

## Edge content audit and long-horizon timestamp semantics

For every symbol with observed Funding coverage, the first and last available monthly archives are downloaded and passed through the frozen Funding parser.

The initial coverage executions reused the source-proof 10 ms tolerance. Runs `32130262060` and `32130438024` were superseded before any Coverage PASS authority after a HYPEUSDT `2026-07` edge archive exposed source `calc_time` jitter of 12 ms around a valid declared 4-hour Funding cadence.

The project did **not** simply raise the tolerance from that single example. A separate read-only all-edge diagnostic (`run 32130801751`, `job 95691293211`) scanned the same 1,440 monthly symbol-period checks and inspected all 30 first/last edge archives:

- 1,440 monthly checks;
- 1,010 `AVAILABLE`;
- 430 `NO_DATA`;
- 30 edge archives;
- 8 edge archives exceeded the 10 ms source-proof tolerance;
- maximum observed absolute cadence residual = **45 ms**;
- no diagnostic edge showed a missing declared 4h/8h Funding event; the deviations remained millisecond-scale timestamp offsets around the declared interval.

Observed edge maxima above 10 ms included:

- SOLUSDT / UNIUSDT / AVAXUSDT `2020-09`: 45 ms;
- SUIUSDT `2023-05`: 28 ms;
- INJUSDT `2022-08`: 21 ms;
- AAVEUSDT `2020-10`: 15 ms;
- BNBUSDT `2020-02`: 15 ms;
- HYPEUSDT `2026-07`: 12 ms.

Before any Coverage PASS authority, the long-horizon edge-audit protocol was therefore re-frozen at **50 ms**. This 50 ms tolerance is authority-scoped to the long-horizon Coverage edge audit; the Source Proof default remains 10 ms.

The tolerance is audit-only. The original source `calc_time` is always preserved exactly. The implementation never rounds, shifts, interpolates or synthesizes a Funding timestamp.

The edge audit verifies:

- official SHA-256 checksum;
- exact CSV member;
- schema;
- finite rates;
- strictly increasing unique raw timestamps;
- source-declared Funding interval;
- cadence residual within the explicitly selected authority-scoped tolerance.

A residual larger than the selected tolerance still fails closed.

Only edge archives are content-downloaded in this discovery phase; interior months are checksum-presence evidence only.

## Interpretation boundary

A Coverage Discovery PASS proves the observed archive boundaries and checksum-backed interior archive presence for the scan window.

It does **not** prove:

- exact listing/delisting dates;
- full interior row-level continuity;
- that Funding onset equals Trade-Kline onset;
- Funding R2 materialization;
- Binance -> Pionex source equivalence;
- Pionex-native Historical Universe membership;
- backtest admission.

The 50 ms Coverage edge tolerance does not retroactively alter the already-frozen 10 ms Funding Source Proof default.

## After PASS

If the discovered 15-symbol scope is materially different from existing cost assumptions, a Funding-specific R2 budget review is required.

Only after the required budget review and a separate explicit Funding materialization authority may Funding archives be downloaded in bulk and written to:

```text
market-data/binance_usdm/perp/{SYMBOL}/funding/year={YYYY}/funding.parquet
```

## Safety boundary

Coverage discovery does not authorize:

- Funding R2 writes;
- bulk Funding materialization;
- provider splicing;
- Pionex-native relabeling;
- source switching;
- Historical Universe membership;
- automatic trade plans;
- live trading.
