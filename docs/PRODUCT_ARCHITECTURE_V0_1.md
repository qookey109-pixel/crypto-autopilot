# Qookey Crypto Autopilot — Product Architecture V0.1

Status date: 2026-09-18

## Product objective

Qookey Crypto Autopilot is a **multi-asset opportunity-selection and automated-trading platform**.

It is **not** a single-coin strategy project and no asset-specific strategy may become the system's primary architecture.

The product priority order is:

1. **Daily Opportunity Engine** — determine which assets are worth attention today.
2. **Strategy Router** — determine which validated strategy family, if any, fits each selected asset and current market regime.
3. **Risk / Position Sizing** — determine stop distance, target risk, feasible position size and leverage constraints.
4. **Portfolio Admission** — apply total-risk, per-asset concentration, strategy-overlap and gross-exposure gates to the explicit proposed basket.
5. **Automated Execution** — only after all upstream gates pass, prepare one deterministic paper cycle from current account state, then require explicit paper submission before fill/lifecycle and account-state advancement; any future live-capable exchange routing remains separately authorized.
6. **Post-trade Learning** — record outcomes and feed research/evaluation systems without silently changing production strategy authority.

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

## Priority 4 — Portfolio admission

Single-route sizing does not establish portfolio safety.

- existing open exposure must be counted before new proposals
- total realized risk must remain within the portfolio budget
- per-asset risk and notional concentration must remain bounded
- overlapping strategy families must not silently multiply correlated exposure
- opposing directions on one symbol require explicit future support
- V0.1 does not invent a strategy ranking or automatically optimize a subset

A risk-safe route may therefore still be rejected at the portfolio layer.

## Priority 5 — Automated execution

Execution is downstream of opportunity selection, strategy compatibility, risk validation and portfolio admission.

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
Paper Account / Position State
        ↓
Paper Cycle Orchestrator
        ↓
Portfolio Admission with current existing exposure
        ↓
paper intents ready for explicit submission
        ↓
Paper Submission Session / exact cycle-id confirmation
        ↓
Repository Paper Broker acceptance
        ↓
Paper Lifecycle Batch / exact session-id confirmation
        ↓
Paper Fill / Order Lifecycle for complete accepted basket
        ↓
account_records
        ↓
Paper Account Advance / exact batch-id confirmation
        ↓
next Paper Account / Position State
        ↓
Paper Loop Checkpoint / exact advance-id confirmation
        ↓
Paper Loop Resume / exact checkpoint-id confirmation
        ↺ next Paper Cycle

Live-paper runtime:
public live market data
        ↓
Live Paper Simulation / tick-by-tick lifecycle progress
        ↓
Checkpoint + Paper Run Store
        ↺ next live-paper tick

Audit sidecar:
completed rounds
        ↓
Paper Loop Integrity / Multi-Cycle Replay
        ↓
Paper Loop Run Package / Transcript
```

Live trading and real-money orders remain separately gated. Product architecture does not itself authorize either.

Paper Fill / Order Lifecycle V0.1 is simulation-only. It may model partial fills,
slippage, fees and protective exits from normalized paper-liquidity inputs, but
it does not establish real order-book depth or live-exchange authority.

Paper Account / Position State V0.1 rebuilds immutable cash/equity/open-position
state from lifecycle evidence and explicit marks. Its open positions feed the
next Portfolio Admission pass as existing exposure; it writes no persistent
broker/account state.

Paper Cycle Orchestrator V0.1 uses that account snapshot as the canonical equity
and exposure source for the next explicit candidate basket. It may prepare
Paper Execution intents, but it performs zero PaperBroker submissions and zero
lifecycle simulations.

Paper Submission Session V0.1 is the separate explicit paper-only submission
boundary. It requires exact cycle-id confirmation, preflights the complete
admitted basket, supports idempotent replay only for identical payloads, and
still grants no scheduling, persistence or live-trading authority.

Paper Lifecycle Batch Coordination V0.1 is the next explicit simulation
boundary. It requires exact session-id confirmation and one caller-supplied
lifecycle input per accepted proposal, reuses the existing single-intent
Lifecycle engine, and emits Account-compatible records without provider or
persistent-state access.

Paper Account Advance V0.1 is the explicit state-transition boundary after a
Lifecycle Batch. It verifies the batch id, replaces latest lifecycle evidence by
paper intent, rematerializes the complete account, and emits the next account
input for another manual cycle without persisting state.

Paper Loop Checkpoint V0.1 verifies the Advance report, rematerializes the next
account again, reconciles Portfolio exposure, and packages the exact
next_account_input plus Account policy with deterministic lineage for the next
manual cycle. It stores nothing.

Paper Loop Resume V0.1 is the explicit checkpoint-consumption boundary. It
requires exact checkpoint-id confirmation, validates the checkpoint again, and
reuses the existing Paper Cycle engine with the carried account input/policy.
It performs zero broker submissions and zero lifecycle simulations.

Paper Loop Integrity / Multi-Cycle Replay V0.1 is audit-only. It verifies two
or more complete forward rounds, recomputes every stage id, requires exact
Checkpoint chaining, checks snapshot/exposure continuity and proves that the
same transcript re-audits to the same deterministic integrity id.

Paper Loop Run Package / Transcript V0.1 is the portable audit sidecar after
Integrity PASS. It re-audits the full transcript, binds every stage payload in a
SHA-256 manifest, embeds the terminal Checkpoint and packages the complete proof
without becoming execution authority.

Live Paper Simulation V0.1 is the public-live-data paper runtime. It may read
current Pionex public order books/trades, advance one active paper basket across
ticks, trigger simulated stop/target lifecycle events, update Paper Account /
Checkpoint state and persist the next deterministic state through Paper Run
Store V0.1. It has no private exchange-order API and cannot create a real order.

Paper Run Store V0.1 provides explicit Local JSON and Cloudflare R2
content-addressed persistence for paper evidence. Storage never upgrades the
stored object's trading authority.

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
