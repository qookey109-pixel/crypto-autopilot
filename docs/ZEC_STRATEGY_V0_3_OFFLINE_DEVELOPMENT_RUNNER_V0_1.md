# ZEC Strategy V0.3 — Offline Development Runner V0.1

Status: **IMPLEMENTATION PREPARED / REAL DEVELOPMENT EXECUTION LOCKED**

## Purpose

This layer implements the deterministic local research mechanics required by the
frozen ZEC V0.3 design without opening fresh confirmation, provider, R2,
holdout, promotion, order or live-trading authority.

The engine supports:

- canonical 15m -> 30m and 15m -> 4h aggregation;
- 30m MACD crossover triggers for the two frozen MACD variants;
- causally available 4h trend context;
- the prior-180-bar 90th-percentile ATR extreme guard using deterministic
  nearest-rank semantics and excluding the current bar;
- adaptive stop distance `max(ATR multiple, 0.5 * full Bollinger width)`;
- account-risk sizing clipped by the frozen 3x leverage ceiling while preserving
  the original stop;
- 6 bps taker fee per side and 5 bps primary development slippage per side;
- explicit funding data when supplied; otherwise funding is reported as
  `UNAVAILABLE_NOT_FABRICATED`;
- fold-boundary marking for still-open positions so one fold cannot leak into
  the next;
- complete candidate x fold matrix validation;
- deterministic robust-first diagnostic ranking;
- local-neighbor enumeration.

## Development selection boundary

The remaining selection ambiguity is now closed by
`config/zec_strategy_v0_3_selection_policy_v0_1.json`.

Before any real V0.3 development matrix is executed, the policy freezes:

- at least 30 realized trades in every development fold;
- worst-fold return strictly above 0%;
- robust-first ranking by worst return, median return, drawdown, trade count,
  then deterministic candidate id;
- at least two independently eligible adjacent neighbors;
- each stable neighbor must retain at least 75% of the selected leader's
  worst-fold return.

The raw ranking object remains diagnostic-only. The separate
`select_zec_v0_3_development_champion(...)` step applies the frozen policy and
returns one of:

- `DEVELOPMENT_CHAMPION_FROZEN`;
- `ISOLATED_DEVELOPMENT_PEAK_REJECTED`;
- `NO_ELIGIBLE_DEVELOPMENT_CANDIDATE`.

Fresh confirmation is never used for development selection and a failed
selection must not silently fall through to the next-ranked candidate.

## Execution authority

The repository contract currently keeps:

`offline_development_runner_authorized = false`

Accordingly, `run_zec_v0_3_development_matrix(...)` fails closed before real
development execution. Unit tests may exercise the pure engine with synthetic
candles, but that is not historical ZEC evidence.

A later explicit authority change may open **local, already-seen development
execution only**. It still must keep the fresh confirmation interval
`2026-08-01T00:00:00Z <= t < 2026-09-16T00:00:00Z` unopened.

## Non-authority

This module does not authorize:

- fresh/provider data reads;
- R2 reads or writes;
- replacement holdout access;
- source switching;
- model/strategy promotion;
- a formal trade plan;
- real-money orders;
- live trading.
