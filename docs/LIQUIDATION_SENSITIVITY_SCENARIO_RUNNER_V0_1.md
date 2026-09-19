# Liquidation Sensitivity Scenario Runner V0.1

Status date: 2026-09-19

Status: **PREPARED — DETERMINISTIC SYNTHETIC SCENARIOS ONLY**

## Purpose

Run a fixed battery of replayable missing-event stress scenarios through the existing liquidation research chain:

`synthetic quality snapshot → deterministic degradation → venue-local summary → coverage sensitivity`.

The runner does not collect exchange data and does not estimate real exchange missingness.

## Fixed scenarios

For one selected venue, V0.1 runs exactly eight deterministic scenarios:

1. drop first event;
2. drop last event;
3. drop largest LONG_LIQUIDATED event;
4. drop largest SHORT_LIQUIDATED event;
5. drop every second event (indices 1, 3, 5, ...);
6. drop all LONG_LIQUIDATED events;
7. drop all SHORT_LIQUIDATED events;
8. drop all events.

Ties for largest notional resolve to the earliest venue-local event index. No randomness or Monte Carlo sampling is used.

## Preconditions

Input must be `synthetic_fixture`. The selected venue must be supported and contain at least two events, including at least one LONG_LIQUIDATED and one SHORT_LIQUIDATED event. Invalid inputs fail closed.

## Output

Each scenario records its explicit drop indices, replayable degradation scenario id, and the existing Coverage Sensitivity V0.1 result. The top-level result explicitly keeps:

- `random_sampling_used = false`
- `estimated_real_missingness_rate = null`
- `correction_weight = null`

These scenarios measure fragility under deliberately constructed event loss. They do not imply that any scenario matches actual Binance, Bybit, or OKX missingness.

## Authority boundary

Authorized: deterministic synthetic stress scenarios and descriptive sensitivity output.

Not authorized: provider/network capture, MCP runtime, real missingness estimation, coverage correction or weighting, cross-venue aggregation, liquidation BUY/SELL signals, Strategy Router authority, R2 writes, holdout access, training, model promotion, real-money orders, or real live trading.
