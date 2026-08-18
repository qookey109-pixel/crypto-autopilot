# Pionex <-> Binance Equivalence Gate V0.1

Updated: 2026-08-18

## Purpose

Freeze the comparison protocol **before** consuming the new live overlap result.

Pionex is the execution-target exchange. Binance USD-M / Binance Vision is a provider-separated long-history candidate. This gate tests whether the two providers are sufficiently aligned for research use without relabelling Binance data as Pionex-native.

## Frozen overlap scope

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- 15 frozen M1A symbols;
- 2026-08-10 08:00:00 UTC through 2026-08-17 07:59:59.999 UTC;
- `15M`, `60M`, `4H`;
- 45 mapped symbol/timeframe pairs.

The protocol is frozen in `config/provider_equivalence_v0_1.json` before the live Binance overlap evidence is run.

## Hard requirements

Every pair must independently pass the existing candle audit for both providers.

Timestamp coverage must be exact. Missing or extra timestamps are a hard `FAIL`; the gate does not interpolate, splice, repair or silently trim mismatched provider histories.

Volume is deliberately **not** an equivalence metric. Exchange-reported volume is venue-specific and cannot be expected to match across Pionex and Binance.

## Price metrics

For every aligned candle, symmetric basis-point differences are computed for O/H/L/C.

### Median OHLC basis

- PASS: <= 10 bps
- REVIEW: >10 and <=25 bps
- FAIL: >25 bps

### P95 open/close basis

- PASS: <=25 bps
- REVIEW: >25 and <=75 bps
- FAIL: >75 bps

### P95 high/low basis

High/low are allowed a wider venue-microstructure tolerance.

- PASS: <=75 bps
- REVIEW: >75 and <=200 bps
- FAIL: >200 bps

## Return behavior

Close-to-close direction agreement compares only the sign of each sequential close change.

- PASS: >=98%
- REVIEW: >=95% and <98%
- FAIL: <95%

This avoids demanding identical price levels while still testing whether the two venues describe the same short-horizon directional path.

## Frozen 60M setup behavior

Only strategy semantics already frozen by Strategy Replay Readiness are compared:

- EMA20 > EMA50;
- EMA20 slope > 0;
- close > EMA20.

At least 100 bars with a comparable setup state are required.

Agreement:

- PASS: >=98%
- REVIEW: >=95% and <98%
- FAIL: <95%

No threshold is invented for the six still-UNDEFINED strategy rules.

## Minimum overlap rows

- `15M`: 600
- `60M`: 150
- `4H`: 40

These limits are below the frozen M1A expected counts (672 / 168 / 42) while still failing materially incomplete overlap.

## Pair and aggregate decisions

A pair is:

- `PASS` if all evaluated dimensions pass;
- `REVIEW` if there is no fail dimension but at least one review dimension;
- `FAIL` if any hard/metric dimension fails.

Aggregate expected pair count: 45.

- `PASS`: all 45 pairs PASS.
- `REVIEW`: zero FAIL pairs and REVIEW fraction <=20%.
- `FAIL`: any FAIL pair, a missing pair, or REVIEW fraction >20%.

All PASS / REVIEW / FAIL results are retained. The thresholds may not be changed after seeing the live result without a new protocol version.

## Critical authorization boundary

**V0.1 never authorizes a full provider source switch.**

Six mandatory strategy semantics are still `UNDEFINED`:

1. ATR-normalized overextension;
2. EMA20 pullback proximity/semantics;
3. EMA20 reclaim semantics;
4. previous-high break semantics;
5. volume-confirmation threshold;
6. structural-stop ATR buffer.

Therefore even an aggregate `PASS` means only that the exact overlap candle path and already-frozen technical/setup behavior passed this protocol. It does not establish complete historical strategy-signal equivalence.

`source_switch_authorized=false` and `trade_plan_authorized=false` remain mandatory.

## Next evidence step

After this protocol is merged and CI-verified:

1. read the frozen Pionex M1A materialization from R2;
2. acquire the same timestamp ranges from the public Binance USD-M Kline API;
3. map symbols syntactically without changing provenance;
4. evaluate all 45 pairs with this exact frozen policy;
5. emit machine-readable pair results and aggregate evidence;
6. freeze the result even if it is REVIEW or FAIL.

No live trading or private exchange API is involved.
