# Live Paper Simulation V0.1

Status date: 2026-09-18

Status: **PREPARED LIVE-PAPER SIMULATION / PUBLIC MARKET DATA ALLOWED / REAL ORDERS CLOSED**

## Meaning of "live"

V0.1 separates two concepts that must not be conflated:

```text
LIVE PAPER
= current public market data
+ current paper decisions
+ simulated fills / stops / targets
+ paper account updates

REAL LIVE TRADING
= private exchange account/order API
+ real funds
+ real exchange orders
```

V0.1 authorizes the first and explicitly forbids the second.

Binding flags:

```text
public_live_market_data_authorized = true
live_paper_simulation_authorized = true
persistent_paper_state_authorized = true

private_exchange_api_authorized = false
real_money_order_authorized = false
live_real_trading_authorized = false
```

## Initial provider

The first live-paper provider is the existing public-only Pionex client.

No API key is used for market data.

V0.1 reads only public:

- order book;
- recent public trades.

It does not expose private balance, position, account or order methods.

## Live paper market frame

Each tick normalizes current public evidence into one
`LivePaperMarketFrame`.

For LONG paper execution:

- best bid / ask provide the current quote;
- bid/ask midpoint is the paper account mark;
- recent public trades since the prior lifecycle frame contribute the observed
  high / low / close range;
- visible ask-side order-book notional is the explicit paper entry-liquidity
  budget;
- the existing Lifecycle participation cap is still applied;
- candle volume is never converted into fake USD liquidity.

The frame timestamp is the explicit tick timestamp. Provider source timestamps
must be causal and within the configured freshness limit.

## Runtime loop

A live-paper state contains:

- latest verified Paper Loop Checkpoint;
- exact Paper Lifecycle policy;
- optional active Session;
- complete lifecycle input history for that active Session;
- latest Lifecycle Batch report;
- last tick timestamp.

The state id is deterministic.

On each tick:

```text
verify state
        ↓
if active Session exists:
append current market frame
        ↓
re-run complete Lifecycle Batch
        ↓
Paper Account Advance
        ↓
new Checkpoint
        ↓
if no active Session remains:
optional explicit candidate basket
        ↓
Resume → Cycle → Session
        ↓
current live market frame
        ↓
Lifecycle Batch → Account Advance → Checkpoint
        ↓
persist next live-paper state
```

This means a paper position that remains open after one tick can hit its real
paper stop or target on a later tick.

## One active basket/session in V0.1

V0.1 deliberately allows only one active Session at a time.

One Session may still contain multiple intents from the same admitted basket.

While any position from that Session remains open, a new Cycle is not opened.

This avoids ambiguous multi-session account-update ordering while establishing
the first persistent live-paper loop.

Overlapping sessions are a future V0.2 concern and require an atomic multi-batch
account reconciliation design.

## Candidate boundary

V0.1 does not invent automatic strategy ranking.

Candidate specs remain explicit upstream inputs and contain:

- existing Paper Cycle candidate payload;
- explicit target price.

All existing Cycle gates still apply:

- account equity basis;
- candidate timestamp causality;
- family validation;
- Portfolio Admission;
- LONG-only Paper Execution authority.

A separate research Strategy Scorecard / Ranking layer may later prepare these
candidate inputs, but ranking does not become order authority automatically.

## Persistence

Live Paper V0.1 may persist the deterministic next state through Paper Run
Store V0.1.

Supported V0.1 storage backends:

- Local JSON with an explicit absolute root;
- Cloudflare R2 through the existing `R2Store`.

Both are content-addressed by object id.

An exact duplicate is an idempotent replay.

Different bytes under the same object id fail closed.

## CLI

Input:

```json
{
  "schema": "qookey-live-paper-tick-input-v0.1",
  "state": {},
  "tick_time_ms": 0,
  "candidate_specs": []
}
```

Run without persistence:

```bash
PYTHONPATH=src python scripts/run_live_paper_tick_v0_1.py \
  --input /tmp/live-paper-tick.json
```

Run with explicit local persistence:

```bash
PYTHONPATH=src python scripts/run_live_paper_tick_v0_1.py \
  --input /tmp/live-paper-tick.json \
  --store-backend local \
  --local-root /absolute/path/to/paper-run-store
```

Run with R2 persistence:

```bash
R2_ACCOUNT_ID=... \
R2_BUCKET=... \
R2_ACCESS_KEY_ID=... \
R2_SECRET_ACCESS_KEY=... \
PYTHONPATH=src python scripts/run_live_paper_tick_v0_1.py \
  --input /tmp/live-paper-tick.json \
  --store-backend r2
```

R2 credentials come only from the environment / secret manager and are never
included in state or reports.

## Holdout boundary

Replacement holdout remains `FROZEN_UNOPENED`.

Live paper market data does not authorize holdout access and is not a substitute
for scientific holdout validation.

## Explicit non-goals

V0.1 does not:

- use Pionex private APIs;
- read balances or real positions;
- create real exchange orders;
- automatically rank strategies;
- allow overlapping active Sessions;
- access replacement holdout;
- promote models or strategies;
- authorize formal real-money trade plans.

## Authority

Live Paper Simulation V0.1 authorizes public live market data, live paper
simulation and paper-state persistence only.

It grants no private exchange API, holdout, real-money order or real-live-trading
authority.
