# Liquidation Cross-Venue Gate V0.1

Status date: 2026-09-19

Status: **PREPARED BLOCKING GATE ONLY**

## Purpose

This gate turns the current research rule into executable behavior:

> venue-local liquidation summaries must not be directly combined into a
> cross-venue liquidation total until missingness and coverage weighting have
> been separately calibrated.

The input is one or more validated:

`qookey-venue-local-liquidation-summary-snapshot-v0.1`

snapshots.

## Behavior

For exactly one venue, the gate returns:

`VENUE_LOCAL_ONLY`

For two or more distinct venues, the gate returns:

`CROSS_VENUE_AGGREGATION_BLOCKED_UNCALIBRATED_COVERAGE`

The gate always emits:

`cross_venue_aggregation_permitted=false`

V0.1 never computes a cross-venue notional, side imbalance, severity score or
venue weight.

## Why this exists

The upstream AgentFeed evaluation documents different observation properties by
venue. The project therefore cannot safely assume that one observed liquidation
dollar on Binance, OKX and Bybit represents the same fraction of underlying
events.

Without a missingness model, direct summation would create false precision.

This gate prevents a future caller from accidentally bypassing that research
boundary merely because venue-local summaries now exist.

## Alignment checks

All summaries in one gate assessment must share:

- symbol;
- `as_of_ms`;
- input class.

Duplicate venues fail closed.

The result copies only minimal metadata:

- venue;
- coverage-quality label;
- event count.

It intentionally does not copy or combine liquidation notionals.

## What would be required to open aggregation later

A future version would need separate evidence for at least:

1. venue-specific observation / throttling behavior;
2. missingness sensitivity;
3. whether a stable correction or weighting method exists;
4. anti-leakage timing;
5. regression tests showing the correction does not create false directional
   signals.

None of those are granted by V0.1.

## Authority

Authorized:

- inspect validated venue-local summary metadata;
- determine whether a request is single-venue or cross-venue;
- block direct cross-venue aggregation.

Not authorized:

- cross-venue aggregation;
- coverage weighting;
- missingness calibration;
- signal generation;
- Strategy Router or Daily Opportunity integration;
- network/MCP access;
- R2 writes;
- holdout access;
- training;
- promotion;
- formal trade plans;
- real-money orders;
- real live trading.
