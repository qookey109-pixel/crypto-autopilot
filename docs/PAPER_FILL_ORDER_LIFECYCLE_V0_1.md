# Paper Fill / Order Lifecycle V0.1

Status date: 2026-09-18

Status: **PREPARED PAPER-SIMULATION-ONLY / NO LIVE AUTHORITY**

## Purpose

Paper Fill / Order Lifecycle V0.1 adds deterministic execution realism after an
intent has already passed:

1. Strategy Family Validation;
2. Risk / Position Sizing;
3. Portfolio Admission;
4. Paper Execution;
5. Repository Paper Broker acceptance.

It does not replace the Repository Paper Broker and it does not modify the
historical backtest engine.

The responsibilities are separated:

- `PaperBroker`: idempotent paper intent recorder;
- `Paper Lifecycle V0.1`: deterministic fill / partial-fill / stop / target
  simulation for an accepted paper intent;
- `backtest.py`: historical strategy replay and performance evaluation.

## Input boundary

Lifecycle V0.1 consumes:

- complete Paper Execution V0.1 evidence;
- one explicit target price;
- normalized chronological OHLC bars;
- explicit `available_notional_usd` for each bar.

Only bars strictly later than the paper intent `as_of_ms` may participate.

The target is an explicit simulation input. Lifecycle V0.1 does not invent a
target or become a strategy exit generator.

## Liquidity contract

V0.1 deliberately does **not** convert provider candle `volume` into assumed
USD executable depth.

Each bar must explicitly provide:

```text
available_notional_usd
```

The frozen default participation cap is 5%.

For example:

```text
available_notional_usd = 1,000
maximum_bar_participation_fraction = 0.05

maximum paper fill on the bar = 50 USD
```

This is a normalized paper-liquidity assumption, not a claim about real
order-book depth.

## Frozen policy

Default V0.1 policy:

- taker fee: 5 bps per fill side;
- adverse entry slippage: 2 bps;
- adverse exit slippage: 2 bps;
- maximum bar participation: 5%;
- maximum entry window: 3 bars;
- same-bar stop/target collision: stop first;
- cancel before first fill if the next market opens through the stop;
- do not chase if the next market opens beyond the target;
- cancel unfilled remainder when entry window expires;
- cancel unfilled remainder when an already-partial position exits;
- do not force-close an open position merely because fixture data ends.

## Causal entry

The paper intent timestamp is the last known decision point.

Lifecycle V0.1 cannot fill on or before that timestamp.

The earliest allowed fill is a later normalized bar.

LONG entry fill price is:

```text
bar open + adverse entry slippage
```

The simulator allocates at most:

```text
available_notional_usd * participation cap
```

per eligible entry bar until:

- requested notional is fully filled;
- the three-bar entry window expires;
- the stop/target invalidates the open position.

## Partial fills

Partial fills are first-class lifecycle events.

Example:

```text
requested notional = 100 USD

bar 1 fill = 50
bar 2 fill = 20
bar 3 fill = 30

filled = 100
unfilled = 0
fill fraction = 1.0
```

If only 30 USD fills by the end of the entry window:

- the remaining 70 USD is cancelled;
- the 30 USD paper position remains open;
- stop/target lifecycle continues for the filled quantity only.

The simulator never increases position size to compensate for missed fills.

## Protective exits

For an existing LONG paper position:

### Stop gap

If a later bar opens below the stop, the stop price is no longer assumed
executable.

The raw exit is the bar open, followed by adverse exit slippage.

### Target gap

If a later bar opens above the target, V0.1 uses the target as the conservative
raw target execution level rather than assuming favorable price improvement.

### Same-bar collision

If one OHLC bar touches both stop and target, the default deterministic policy is
`STOP_FIRST`.

This matches the existing project's conservative backtest principle without
sharing the same runtime implementation.

## Costs

V0.1 records:

- entry fee;
- exit fee;
- adverse entry slippage;
- adverse exit slippage;
- gross PnL;
- net PnL.

Funding is deliberately not modeled yet.

## Lifecycle outcomes

### CLOSED

A filled or partially filled position hits:

- STOP;
- STOP_GAP;
- STOP_SAME_BAR_COLLISION;
- TARGET;
- TARGET_GAP;
- TARGET_SAME_BAR_COLLISION; or
- END_OF_DATA only when explicitly enabled by policy.

### OPEN_POSITION

Some quantity is filled but no exit occurs before supplied data ends.

V0.1 does not fabricate a closing trade by default.

### CANCELLED_UNFILLED

No position is opened because:

- no future market bar exists;
- the stop is invalidated before first fill;
- the market opens beyond the target before first fill;
- the entry window expires without any fill.

## Lineage

A lifecycle plan is SHA-256-derived from:

- exact Paper Execution intent id;
- symbol;
- LONG side;
- intent timestamp;
- requested notional;
- stop;
- explicit target.

The Paper Execution evidence parser also rechecks:

- zero automatic-submission authority;
- zero SHORT paper authority;
- zero formal-trade-plan authority;
- zero real-money order authority;
- zero live-trading authority;
- accepted receipt / intent consistency.

## CLI

A no-network simulation entrypoint is provided:

```bash
PYTHONPATH=src python scripts/simulate_paper_lifecycle_v0_1.py \
  --input /tmp/paper-lifecycle-input.json
```

Input schema:

```json
{
  "schema": "qookey-paper-fill-lifecycle-input-v0.1",
  "paper_execution_evidence": {},
  "target_price": 105.0,
  "bars": [
    {
      "time_ms": 2000,
      "open": 100.0,
      "high": 101.0,
      "low": 99.0,
      "close": 100.0,
      "available_notional_usd": 4000.0
    }
  ]
}
```

The complete Paper Execution evidence object is required.

A lifecycle cancellation is a valid simulation result and does not mean the CLI
failed. Invalid input/config returns exit status 2.

## Deliberate limitations

V0.1 does not claim to model:

- real order-book depth;
- queue priority;
- maker fills;
- latency;
- exchange throttling;
- liquidation;
- cross-margin interaction;
- funding settlement;
- exchange rejection;
- persistent broker state;
- SHORT paper lifecycle.

Those require additional evidence or dedicated later versions.

## Batch coordination

Paper Lifecycle Batch Coordination V0.1 wraps this same single-intent engine for
the complete accepted Paper Submission Session basket.

It adds no second fill model. It canonicalizes proposal order, verifies exact
session lineage, invokes this lifecycle engine once per accepted intent and
emits Paper Account-compatible records.

## Downstream account state

Paper Account / Position State V0.1 consumes the latest lifecycle evidence
together with the matching Paper Execution evidence.

It rebuilds:

- paper cash and equity;
- closed realized net PnL;
- open entry fees;
- open mark-to-market PnL;
- open position state;
- current exposure for the next Portfolio Admission pass.

Lifecycle remains responsible for fill/exit semantics. The account layer does
not close a position merely because a later mark crosses a protective boundary;
it fails closed and requires lifecycle advancement first.

## Authority

Paper Fill / Order Lifecycle V0.1 grants paper simulation only.

It grants no provider access, R2 access, replacement-holdout access, persistent
broker writes, automatic/scheduled submission, SHORT paper execution, formal
trade-plan authority, real-money order authority or live-trading authority.
