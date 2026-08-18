# Binance Staged Multi-Year Expansion Plan V0.1

## Purpose

Turn the frozen Maximum-Available Binance Historical Coverage authority into a deterministic, reviewable sequence of future trade-Kline expansion waves without downloading history or writing anything to R2.

This is a **planning-only** phase. A successful plan is not materialization authority.

## Authorities

- Coverage: `research/receipts/2026-08-18-binance-max-coverage-discovery.json`
- Observed capacity: `research/receipts/2026-08-18-binance-observed-r2-budget.json`
- Existing materialization: `research/receipts/2026-08-18-binance-2025-r2-pilot.json`

The frozen 15-symbol M1A universe remains the only candidate universe in scope.

## Planning scope

Included:

- Binance USD-M / Binance Vision trade Klines only
- project intervals `15M`, `60M`, `4H`
- existing partition convention: monthly `15M`, annual `60M`, annual `4H`
- only source months inside the frozen observed strategy-price common coverage window

Excluded:

- Mark Price materialization
- Funding materialization
- Open Interest beyond its separately bounded provider window
- historical liquidity
- historical SState
- Pionex-native relabeling
- provider splicing
- any strategy-parameter update
- R2 writes
- private API calls
- order execution

## Wave policy

The planner derives years from authority rather than hard-coding an eight-year assumption.

1. Keep 2025 excluded because the 2025 Binance R2 pilot is already frozen PASS.
2. Defer the current incomplete year.
3. Start with the newest complete, unmaterialized historical year.
4. Move backward one year at a time until the oldest observed authority year.
5. Include a symbol only if its frozen coverage intersects that year.
6. For a symbol's first observed year, include only observed months from the onset month onward.
7. Never synthesize pre-onset months.

With the current frozen authority, the expected historical wave years are `2024 -> 2023 -> 2022 -> 2021 -> 2020`.

## Capacity estimation

The planner reuses the observed 2025 Binance R2 capacity authority:

- 45,990 rows per full market-year
- observed bytes-per-row from the frozen 2025 pilot
- partial onset months are counted as a full month-equivalent for planning, so partial availability cannot make the budget look artificially cheaper
- canonical + retained staging and 3x stress multipliers are inherited from the frozen observed-capacity authority

These are planning estimates only. Any materially larger market count, additional dataset, or changed partition scheme requires a new budget review before writes.

## Materialization prerequisites

No wave may execute until all of the following exist:

- `PIONEX_BINANCE_EQUIVALENCE_GATE_PASS_AUTHORITY`
- long-horizon Historical Universe review
- explicit staged-expansion authority naming the exact wave/scope

Coverage PASS by itself does not authorize source switching or backfill.

## Expected planning result

A successful workflow emits:

- `execution_status = PASS`
- `plan_status = READY_FOR_REVIEW`
- deterministic historical waves
- per-wave symbol/month membership
- source-archive and future R2-object counts
- conservative row/storage estimates
- current incomplete year explicitly deferred
- `materialization_authorized = false`
- `source_switch_authorized = false`
- `r2_writes_performed = false`

## Safety boundary

The plan must never be interpreted as approval for:

- 8 years x ~250 markets
- Binance -> Pionex source substitution
- Pionex-native provenance
- Mark Price/Funding completion
- strategy replay authority
- live trading

The next action after a planning PASS is an authority review of the plan, not a bulk download.
