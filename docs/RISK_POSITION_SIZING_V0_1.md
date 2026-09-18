# Risk / Position Sizing V0.1

Status date: 2026-09-18

Status: **PREPARED RESEARCH-ONLY / NO EXECUTION AUTHORITY**

## Purpose

Risk / Position Sizing V0.1 is the first product-stage implementation of the
architecture rule:

> market structure decides where the trade is invalidated; account risk decides
> how large the position may be.

The sizing layer consumes an already chosen direction, entry price and upstream
stop. It does not invent or tighten the stop to force a target risk budget.

## Core separation

The V0.1 flow is:

```text
upstream strategy / market invalidation
        ↓
entry + stop distance
        ↓
account target risk budget
        ↓
target notional
        ↓
leverage / notional constraints
        ↓
approved notional
        ↓
realized risk
```

Target risk and realized risk are recorded separately.

If constraints prevent full deployment, the correct behavior is to reduce
position size and leave the stop unchanged.

## Frozen default policy

The versioned default in
`config/risk_position_sizing_v0_1.json` is:

- target risk per position: 1% of equity
- maximum leverage: 3x
- daily new-position shutdown after -3R realized
- maximum new positions per day: 3
- generic minimum notional: 0 USD
- generic maximum notional: none

The generic notional defaults are intentionally not exchange-specific. V0.1
does not invent Pionex/Binance/MAX lot-size or precision rules. Those constraints
must be supplied by a later exchange-specific integration when authoritative
metadata exists.

## Sizing math

For either LONG or SHORT:

```text
stop_distance_fraction = abs(entry - stop) / entry

target_risk_usd = equity_usd * risk_fraction_per_trade

target_notional_usd =
    target_risk_usd / stop_distance_fraction

required_leverage =
    target_notional_usd / equity_usd
```

The feasible notional is bounded by:

```text
equity * max_leverage
optional maximum_notional_usd
```

Then:

```text
realized_risk_usd =
    approved_notional_usd * stop_distance_fraction

risk_utilization_fraction =
    realized_risk_usd / target_risk_usd
```

## Example — leverage clipping

Assume:

- equity = 100 USD
- LONG entry = 100
- stop = 99.8
- target risk = 1%
- max leverage = 3x

The stop distance is 0.2%.

Full 1 USD risk would require:

```text
target notional = 1 / 0.002 = 500 USD
required leverage = 5x
```

V0.1 does **not** move the stop closer.

Instead:

```text
approved notional = 300 USD
realized leverage = 3x
realized risk = 300 * 0.002 = 0.60 USD
risk utilization = 60%
```

The original 99.8 stop is preserved.

## Minimum notional behavior

If an exchange minimum notional is larger than the maximum safe position size,
V0.1 returns:

`NO_TRADE / minimum_notional_exceeds_safe_size`

It does not increase notional above the risk budget just to satisfy an exchange
minimum.

## LONG / SHORT research symmetry

`plan_position_size()` supports both LONG and SHORT geometry:

- LONG stop must be below entry
- SHORT stop must be above entry

This is research sizing symmetry only.

Current project governance still does **not** authorize SHORT execution.

## Daily gates

Sizing fails closed when:

- realized daily R <= -3R
- new positions today >= 3
- direction is unsupported
- equity or prices are invalid
- stop is on the wrong side of entry
- runtime values are non-finite
- minimum notional cannot be satisfied safely

## Relationship to existing risk.py

The existing `size_long_trade()` API remains intact for compatibility with
older Paper baseline tests and historical callers.

V0.1 adds:

- `PositionSizingPolicy`
- `PositionSizingPlan`
- `plan_position_size()`
- `position_sizing_policy_from_config()`

The new planner is the product-stage research sizing path. It does not rewrite
historical behavior behind the old API.

## CLI

The CLI performs no provider, R2, broker or order operation:

```bash
PYTHONPATH=src python scripts/plan_position_size.py \
  --direction LONG \
  --equity-usd 100 \
  --entry-price 100 \
  --stop-price 99.8
```

It emits a deterministic JSON report containing target risk, realized risk,
target/approved notional, leverage, clipping reasons and the preserved stop.

## What V0.1 deliberately does not infer

V0.1 does not infer:

- stop placement
- exchange lot size
- quantity step
- tick size
- liquidation price
- margin mode
- portfolio correlation
- cross-position risk budget
- execution slippage
- funding impact

Those belong to upstream strategy invalidation, later exchange-constraint
integration, portfolio risk or execution layers.

## Anti-gambling invariants

The V0.1 contract explicitly disallows:

- martingale
- loss doubling
- unlimited averaging down
- stop tightening to consume target risk

## Authority

Risk / Position Sizing V0.1 grants no provider access, R2 access, replacement
holdout access, source switch, strategy/model promotion, paper execution, SHORT
execution, formal trade-plan authority, real-money order authority or live
trading authority.
