# Liquidation Coverage Sensitivity V0.1

Status date: 2026-09-19

Status: **PREPARED SYNTHETIC SENSITIVITY ONLY**

## Purpose

This layer measures how much a venue-local liquidation summary can move when a
synthetic fixture is intentionally degraded.

It answers a narrow research question:

> If events are missing, how sensitive are event counts, liquidation notionals
> and long/short imbalance?

It does **not** answer:

> What is the real missingness rate of Binance, OKX or Bybit?

and it does not produce a correction factor.

## Input boundary

V0.1 accepts two validated
`qookey-venue-local-liquidation-summary-snapshot-v0.1` objects:

1. a synthetic reference summary;
2. a synthetic degraded summary.

Both must have:

- `input_class=synthetic_fixture`;
- the same symbol;
- the same venue;
- the same `as_of_ms`.

The degraded fixture cannot contain more events than the reference fixture.

## Output

The report contains:

- event-count retention;
- long-liquidated notional retention;
- short-liquidated notional retention;
- gross-notional retention;
- largest-event retention;
- side-imbalance delta;
- whether the sign of side imbalance changed.

These fields show sensitivity only.

V0.1 explicitly outputs:

```text
correction_weight = null
estimated_real_missingness_rate = null
```

## Why synthetic only

The current project evidence establishes that venue observation properties
differ, but it does not establish a reliable real-world missingness rate that
can be used as a correction.

Using synthetic degradation lets us test whether a statistic is fragile without
pretending we know the true correction.

## No routing or trading authority

A sign change in side imbalance is descriptive evidence that missingness can
alter interpretation. It is not a BUY/SELL signal and cannot alter the Strategy
Router.

Likewise, a retention ratio is not a venue weight.

## Authority

Authorized:

- deterministic comparison of two same-venue synthetic summaries;
- sensitivity metrics only.

Not authorized:

- estimating actual venue missingness;
- correction or weighting;
- cross-venue aggregation;
- signals;
- Strategy Router / Daily Opportunity integration;
- network/MCP access;
- R2 writes;
- holdout access;
- training;
- model promotion;
- formal trade plans;
- real-money orders;
- real live trading.
