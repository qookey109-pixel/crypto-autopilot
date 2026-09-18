# Qookey Crypto Autopilot — Product Architecture V0.1

Status date: 2026-09-18

## Product objective

Qookey Crypto Autopilot is a **multi-asset opportunity-selection and automated-trading platform**.

It is **not** a single-coin strategy project and no asset-specific strategy may become the system's primary architecture.

The product priority order is:

1. **Daily Opportunity Engine** — determine which assets are worth attention today.
2. **Strategy Router** — determine which validated strategy family, if any, fits each selected asset and current market regime.
3. **Risk / Position Sizing** — determine stop distance, target risk, feasible position size and leverage constraints.
4. **Automated Execution** — only after all upstream gates pass, route a paper/live-capable execution plan through the appropriate exchange adapter under separately authorized trading authority.
5. **Post-trade Learning** — record outcomes and feed research/evaluation systems without silently changing production strategy authority.

## Priority 1 — Daily Opportunity Engine

The system must begin with the governed multi-asset universe rather than a preselected coin.

Candidate generation may use only point-in-time evidence available at the decision timestamp, including where governed and available:

- data quality and freshness
- market availability and liquidity
- trend / regime
- realized volatility
- technical structure
- breakout / momentum evidence
- risk and execution-cost estimates
- strategy compatibility
- statistical research evidence

The engine may output zero candidates. The product must never force a fixed number of daily trades.

Its output is a **research/trading candidate set**, not an automatic order instruction.

## Priority 2 — Strategy Router

Each candidate asset is routed to zero or more compatible strategy families.

Examples include:

- trend-following
- breakout
- momentum
- mean-reversion
- volatility-aware strategies
- future microstructure / execution-aware strategies

A strategy family must be validated as a reusable module across its declared asset/regime scope. Asset-specific experiments may inform a module but cannot redefine the product around that asset.

If no strategy has adequate evidence for the candidate and regime, the router returns `NO_TRADE`.

## Priority 3 — Risk and position sizing

Stop placement and account-risk budgeting are independent.

- market structure / volatility determines how far the stop must be
- risk budget determines how much notional can be used
- leverage and exchange constraints bound the feasible position
- the system must not tighten a volatility-valid stop merely to consume a target risk budget
- target and realized risk must both be recorded when leverage/margin constraints prevent full target risk from being deployed

No martingale, loss doubling or unlimited averaging down is allowed.

## Priority 4 — Automated execution

Execution is downstream of opportunity selection, strategy compatibility and risk validation.

The intended flow is:

```text
Governed multi-asset universe
        ↓
Daily Opportunity Engine
        ↓
Candidate assets / NO_TRADE
        ↓
Strategy Router
        ↓
Validated strategy + regime match / NO_TRADE
        ↓
Risk & Position Sizing
        ↓
Paper execution
        ↓
Exchange adapter
        ↓
Order / stop / exit monitoring
        ↓
Trade journal and research feedback
```

Live trading and real-money orders remain separately gated. Product architecture does not itself authorize either.

## Single-asset research boundary

BTC, ETH, SOL, ZEC or any other individual asset may have dedicated research experiments.

Those experiments are **modules and evidence**, not the platform architecture.

For example, ZEC Strategy V0.3 is allowed to answer:

> Does this regime-aware MACD/ATR/Bollinger strategy family show evidence on ZEC?

It is not allowed to change the system objective into:

> Trade ZEC every day.

If a single-asset result later generalizes, it must enter the Strategy Router through a separate multi-asset/generalization validation path.

## Governance

This document defines product architecture and priority, not execution authority.

It does not authorize:

- new provider access
- new R2 access
- holdout access
- source switching
- model promotion
- automatic strategy mutation
- formal trade plans
- real-money orders
- live trading

Repository `main`, current versioned configs, receipts and immutable run evidence remain authoritative for operational permissions.
