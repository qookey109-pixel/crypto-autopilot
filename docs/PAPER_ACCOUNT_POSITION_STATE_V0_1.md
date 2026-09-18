# Paper Account / Position State V0.1

Status date: 2026-09-18

Status: **PREPARED PAPER-STATE-ONLY / NO LIVE AUTHORITY**

## Purpose

Paper Account / Position State V0.1 turns accepted paper execution and lifecycle
evidence into one coherent account snapshot.

The product flow is now:

```text
Daily Opportunity
        ↓
Strategy Router
        ↓
Family Validation
        ↓
Risk / Position Sizing
        ↓
Portfolio Admission
        ↓
Paper Execution Intent
        ↓
Repository Paper Broker
        ↓
Paper Fill / Order Lifecycle
        ↓
Paper Account / Position State
        ↓
existing open exposure back into Portfolio Admission
```

This closes the first deterministic paper-state loop without enabling
unattended or live trading.

## V0.1 state model

V0.1 does not maintain a mutable database.

Instead it rebuilds one immutable snapshot from:

- one declared initial paper equity;
- the **latest** lifecycle report for each paper intent;
- the matching Paper Execution evidence;
- one explicit current mark per open symbol.

The same input produces the same snapshot id.

A lifecycle may move from OPEN_POSITION to CLOSED in later evidence, but an
account-materialization input must contain only the latest report for that
lifecycle id.

Duplicate lifecycle ids or multiple lifecycles for one paper intent fail closed.

## Accounting model

This project models USD-M derivative-style paper exposure.

V0.1 therefore does **not** subtract full derivatives notional from cash.

### Closed position

The lifecycle result already contains net PnL after modeled entry/exit fees.

```text
cash += closed lifecycle net_pnl_usd
```

### Open position

Entry fee has already occurred, so:

```text
cash -= open entry fee
```

Open mark-to-market is:

```text
unrealized gross PnL =
    (mark price - average entry price) * LONG quantity
```

Account equity is:

```text
equity =
    initial equity
    + closed net PnL
    - entry fees on still-open positions
    + open unrealized gross PnL
```

V0.1 does not reserve a hypothetical future exit fee in unrealized PnL.

## Open-position marks

Marks are explicit inputs. Account V0.1 performs no provider request.

For every open symbol:

- exactly one mark is required;
- extra marks for symbols with no open position are rejected;
- mark timestamp cannot precede the latest lifecycle event;
- by default all marks must share the same timestamp.

This creates a coherent point-in-time account snapshot.

## Protective-boundary rule

An OPEN_POSITION lifecycle says its stop/target has not yet been triggered.

If a later mark is already:

- at/below the LONG stop; or
- at/above the target,

Account V0.1 rejects the stale state.

The lifecycle must be advanced first.

The account layer does not silently close the trade from a mark because fill,
gap and slippage behavior belongs to Paper Fill / Order Lifecycle.

## Account states

### ACCOUNT_ACTIVE

Paper equity is above the configured insolvency floor.

### ACCOUNT_INSOLVENT

Paper equity is at or below the insolvency floor.

An insolvent account cannot export new Portfolio Admission capacity.

This prevents an insolvent snapshot from appearing as an empty book that could
accept new trades.

## Portfolio feedback

Each current open position can be exported as a Portfolio Admission
`PortfolioExposure`.

For V0.1:

```text
current notional =
    mark price * filled quantity

portfolio stop risk =
    (mark price - stop price) * LONG quantity
```

The stop-risk value represents the current mark-to-stop loss budget, not the
original pre-fill sizing estimate.

This is intentionally recomputed from the actual partial/full fill quantity and
current mark.

The Portfolio Admission layer can therefore count live paper-state exposure
before evaluating a new basket.

## Evidence validation

Account V0.1 revalidates the upstream evidence rather than trusting fields
blindly.

Paper Execution evidence must remain:

- Repository-Paper-Broker-only;
- provider-free;
- R2-free;
- holdout-free;
- automatic-submission-free;
- SHORT-paper-free;
- formal-trade-plan-free;
- real-money-free;
- live-trading-free.

Lifecycle evidence must remain:

- paper-simulation-only;
- provider-free;
- R2-free;
- holdout-free;
- persistent-state-write-free;
- automatic-submission-free;
- real-money-free;
- live-trading-free.

It also rechecks:

- intent / receipt / lifecycle ids;
- symbol and LONG side;
- requested notional lineage;
- filled + unfilled = requested;
- fill fraction consistency;
- OPEN / CLOSED / CANCELLED accounting fields;
- lifecycle event chronology.

A manually altered lifecycle report therefore cannot silently enter the account.

## CLI

A no-network state materializer is provided:

```bash
PYTHONPATH=src python scripts/materialize_paper_account_v0_1.py \
  --input /tmp/paper-account-input.json
```

Input shape:

```json
{
  "schema": "qookey-paper-account-state-input-v0.1",
  "initial_equity_usd": 100.0,
  "records": [
    {
      "paper_execution_evidence": {},
      "paper_lifecycle_report": {}
    }
  ],
  "marks": [
    {
      "symbol": "BTC_USDT_PERP",
      "time_ms": 3000,
      "price": 100.5
    }
  ]
}
```

The complete upstream evidence objects are required.

Output contains:

- immutable account snapshot;
- cash;
- equity;
- closed realized net PnL;
- open entry fees;
- open unrealized gross PnL;
- open positions;
- lifecycle SHA-256 lineage;
- Portfolio Admission-compatible existing exposures.

No state is persisted.

## Deliberate limitations

V0.1 does not model:

- funding settlement;
- margin maintenance;
- isolated/cross margin;
- liquidation;
- realized tax lots;
- deposits or withdrawals;
- persistent database storage;
- SHORT positions;
- multiple collateral currencies;
- exchange balances.

Those require later contracts and evidence.

## Authority

Paper Account / Position State V0.1 grants only deterministic paper-state
materialization and exposure export.

## Downstream cycle preparation

Paper Cycle Orchestrator V0.1 uses the immutable account snapshot as the
canonical equity/timestamp source for the next explicit candidate basket.

Open positions are exported as existing Portfolio Admission exposure before any
new paper intent can become ready.

The cycle layer still performs no PaperBroker submission, lifecycle simulation
or persistent state write.

## Authority

Paper Account / Position State V0.1 grants only deterministic paper-state
materialization and exposure export.

It grants no provider access, R2 access, replacement-holdout access, persistent
state writes, automatic/scheduled submission, SHORT paper execution, formal
trade-plan authority, real-money order authority or live-trading authority.
