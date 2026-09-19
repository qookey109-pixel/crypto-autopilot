# Venue-local Liquidation Summary V0.1

Status date: 2026-09-19

Status: **PREPARED RESEARCH SUMMARY ONLY**

## Purpose

This layer consumes a validated
`qookey-liquidation-quality-context-snapshot-v0.1` and creates a summary for
**one venue at a time**.

It exists to let research inspect liquidation pressure without erasing the
venue-quality differences preserved by Liquidation Quality Context V0.1.

## Output

For one requested venue, V0.1 returns:

- event count;
- long-liquidated USD notional;
- short-liquidated USD notional;
- gross liquidated USD notional;
- long-minus-short side imbalance;
- largest event notional;
- first and last event timestamps;
- the venue's preserved coverage-quality label.

The side imbalance is descriptive only:

```text
(long_liquidated_notional - short_liquidated_notional)
------------------------------------------------------
          gross_liquidated_notional
```

It is **not** a BUY/SELL signal.

## Why there is no cross-venue total

The source-quality contract preserves materially different coverage properties
for Bybit, Binance and OKX.

V0.1 therefore refuses to combine venues, weight venues or create a global
liquidation score.

Before any future cross-venue statistic is considered, research needs a
separate missingness / sampling-bias study.

## Coverage consistency

A venue-local summary also rejects a snapshot if the selected venue contains
multiple coverage-quality labels.

That forces callers to resolve capture degradation explicitly instead of
silently mixing trusted and degraded intervals into one summary.

## Empty venue behavior

If a valid liquidation-quality snapshot has no events for the requested venue,
V0.1 returns a zero-event summary with:

- zero notionals;
- zero side imbalance;
- no first/last timestamp;
- no inferred coverage label.

It does not fabricate missing observations.

## Authority

Authorized:

- summarize one venue from an already validated liquidation-quality snapshot;
- deterministic arithmetic only.

Not authorized:

- cross-venue aggregation;
- venue weighting;
- signal generation;
- Strategy Router or Daily Opportunity integration;
- network / MCP access;
- R2 writes;
- holdout access;
- training;
- model promotion;
- formal trade plans;
- real-money orders;
- real live trading.
