# Historical SState Replay V0.1

## Purpose

Historical SState Replay V0.1 is a strict read-only boundary for replaying **already recorded** SState outputs during historical research.

It does not reproduce SState logic, does not fit/calibrate SState, and does not infer missing historical states.

## Exact-bar authority

Every `HistoricalSStatePoint` freezes:

- symbol,
- source bar identity (`bar_time_ms`),
- the earliest time the output was actually available (`available_at_ms`),
- the unchanged `SStateContext`,
- source reference,
- optional source SHA-256.

Historical replay requires authority for the exact `(symbol, bar_time_ms)` pair.

A prior SState value is **not** automatically carried forward to an unrecorded bar. This is deliberately conservative because implicit carry-forward can create stale-context or hidden lookahead assumptions.

## Availability anti-leakage gate

Even when a point exists for a historical bar, it cannot be read before its recorded availability time:

```text
point.available_at_ms <= as_of_ms
```

A request before that boundary raises `HistoricalSStateNotAvailableError`.

This is separate from Technical Features V0.1 closed-bar timing and from Backtest Engine next-bar fill timing. Together the boundaries are:

1. candle-derived technical values cannot be used until the candle closes,
2. recorded SState output cannot be used until its own availability timestamp,
3. a resulting strategy signal cannot fill on the signal bar and must wait for the next bar.

## No recomputation

The replay provider returns the stored `SStateContext` unchanged. It does not:

- alter state labels,
- recalculate probability,
- change sample count,
- reinterpret the probability as an intraday trade win rate.

The existing strategy rule remains that SState historical probability is a background gate only.

## Conflict gate

Multiple non-identical points for the same `(symbol, bar_time_ms)` are rejected with `HistoricalSStateConflictError`.

Identical duplicate objects may be deduplicated. Conflicting source authority must be reconciled outside the replay layer before it may influence a backtest.

## Validation

V0.1 validates:

- non-empty symbol/source reference,
- non-negative timestamps,
- `available_at_ms >= bar_time_ms`,
- non-empty SState label,
- non-negative sample count,
- probability is either unavailable (`None`) or finite within `[0, 1]`,
- optional source SHA-256 is a 64-character hex digest.

## Current boundary

This foundation does **not** mean real historical SState data has been acquired.

The project still needs a separate evidence-producing ingestion path that supplies real historical SState outputs and their true availability timestamps. Until then, tests/fixtures can exercise the replay contract but cannot be treated as historical strategy authority.

## Safety

Historical SState Replay V0.1:

- does not modify SState core,
- does not infer or interpolate missing SState outputs,
- does not use private Pionex API,
- does not submit orders,
- does not authorize live trading,
- remains research/backtest infrastructure only.
