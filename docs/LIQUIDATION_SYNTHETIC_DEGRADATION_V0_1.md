# Liquidation Synthetic Degradation V0.1

Status date: 2026-09-19

Status: **PREPARED SYNTHETIC FIXTURE TRANSFORM ONLY**

## Purpose

This layer creates deterministic degraded liquidation fixtures for the
Liquidation Coverage Sensitivity V0.1 harness.

It starts from an already validated
`qookey-liquidation-quality-context-snapshot-v0.1` whose
`input_class` is `synthetic_fixture`.

The caller selects one venue and explicitly supplies the event indices to drop.

There is no randomness.

## Deterministic degradation

Example:

```text
venue = binance
drop_event_indices = [1, 3]
```

The indices are relative to Binance events in their existing validated order.

Running the same snapshot with the same index list produces the same degraded
fixture and the same scenario id:

```text
drop_indices:1,3
```

This makes sensitivity experiments replayable and auditable.

## Coverage labeling

All retained events in the selected venue are relabeled:

`DEGRADED_OR_UNKNOWN`

The transform does not claim that the resulting synthetic missingness resembles
the real exchange.

It explicitly outputs:

```text
real_missingness_rate_estimate = null
correction_weight = null
random_sampling_used = false
```

## One venue per degraded fixture

The output contains only the selected venue.

This is intentional. The synthetic degradation experiment is designed to feed
the venue-local summary and then the synthetic sensitivity harness without
silently creating a cross-venue comparison.

## Fail-closed rules

V0.1 rejects:

- non-synthetic input classes;
- unknown snapshot schema;
- a venue with no events;
- negative indices;
- boolean indices;
- duplicate indices;
- out-of-range indices;
- an empty drop list.

Dropping all events is allowed because a zero-observation scenario is useful for
stress testing.

## Authority

Authorized:

- deterministic synthetic event removal;
- coverage downgrade to `DEGRADED_OR_UNKNOWN`;
- replayable scenario metadata.

Not authorized:

- estimating real missingness;
- random sampling;
- correction weights;
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
