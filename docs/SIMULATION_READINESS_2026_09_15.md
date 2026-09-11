# Simulation Readiness — 2026-09-15

Status: **INTEGRATION PREPARED — NOT YET ON `main` — NOT FULL_SIMULATION_READY**

This document is the short operational map for the 2026-09-15 paper/simulation target. It does not replace historical receipts and does not claim that any Draft PR has already become Repository authority.

## Safety boundary

The target is simulation/paper execution only.

Not authorized by this integration:

- real-money orders;
- live trading;
- private Pionex account API access;
- source switching;
- replacement-holdout access;
- automatic model promotion;
- automatic historical-materialization schedules.

The new Pionex control-plane workflows are manual `workflow_dispatch` only and use public market-data endpoints without an API key.

## Current evidence already established

### Pionex V0.2 bounded K-line pilot

A valid post-merge production run already proved one exact `BTC_USDT_PERP` capacity sample:

- `15M`: 2,592 rows;
- `60M`: 648 rows;
- `4H`: 162 rows;
- fixed window: 2026-08-01 through 2026-08-27 UTC;
- R2 publication completed with latest-pointer-last semantics;
- replacement holdout remained unopened.

This is a bounded 27-day sample, not a full-history claim.

## Manual public control plane prepared by this integration

### 1. Historical Reach Discovery V0.3

Workflow: `pionex-historical-reach-v0-3.yml`

Purpose: determine how far the public Pionex K-line API can actually be traversed for `BTC_USDT_PERP` at:

- `15M`;
- `60M`;
- `4H`;
- `1D`;
- `1W`.

Each interval stops either at a proven provider-earliest boundary or the documented 10,000-record ceiling. `1Y` is not provider-native and remains a later derivation from validated `1D` evidence.

BTC reach is provider-reference evidence only. It must never be copied to another market as proof of that market's listing history.

### 2. Pionex Research Universe 150+ V0.1

Workflow: `pionex-research-universe-v0-1.yml`

Exactly three public snapshot requests feed the deterministic selector:

1. live PERP symbols;
2. PERP tickers;
3. PERP book tickers.

The selector requires at least 150 quality-valid markets and retains:

- a 100-market Pionex-liquidity crypto core;
- quality-valid explicit meme-watchlist matches;
- quality-valid tokenized-equity / fund / metals registry matches;
- deterministic fill from remaining crypto when needed.

This is not a claim of global market-cap Top 100.

### 3. Tiered 150+ history planner V0.1

No provider execution is performed by the planner.

Profiles:

- `FULL_INTRADAY`: at most 30 markets → `15M / 60M / 4H / 1D / 1W`;
- `MULTISCALE_RESEARCH`: remaining core/meme markets → `60M / 4H / 1D / 1W`;
- `BREADTH_BACKGROUND`: remaining selected markets → `1D / 1W`.

Every market must independently prove its own earliest provider boundary during a later materialization stage.

### 4. Pionex Funding History V0.1

Workflow: `pionex-funding-history-v0-1.yml`

Purpose: obtain the missing provider-native funding input for the same BTC V0.2 sample window.

Contract:

- public `/api/v1/market/fundingRates`;
- `BTC_USDT_PERP`;
- 2026-08-01 inclusive through 2026-08-28 exclusive;
- page limit 500;
- at most 3 provider requests;
- zero automatic retries;
- no fixed funding-cadence assumption;
- no zero-fill or interpolation;
- no Binance-as-Pionex substitution.

A PASS capture remains evidence only. It does not automatically admit production data into the simulator.

## Simulation engine dependency

The execution-correctness and candle-driven Simulation Readiness V0.3 work remains in PR #255 and must be reviewed into the consolidated path before `FULL_SIMULATION_READY` can be considered.

That work includes:

- non-finite risk inputs fail closed;
- gap-through-stop execution at the first available price;
- kill switch;
- maximum holding time;
- candle-driven 4H/60M/15M simulation-only signal generation;
- canonical risk/backtest execution rather than a second broker path.

## Required evidence sequence after reviewed merge

The shortest safe sequence is:

1. manually run Historical Reach Discovery and freeze its secret-free report;
2. manually run the 150+ Universe Snapshot and freeze its secret-free report;
3. feed the two reviewed reports into the deterministic 150+ history planner;
4. manually run bounded Pionex Funding History capture and freeze its report;
5. review a separate historical-materialization authority based on the measured reach and planner capacity;
6. integrate/admit exact K-line + funding evidence into Simulation Readiness V0.3;
7. run paper/historical simulation and emit PnL, drawdown, trade ledger, modeled fees/slippage/funding, kill-switch and readiness results;
8. declare `READY` only if the final readiness gate passes. Otherwise declare `NOT_READY` with explicit blockers.

## What this integration deliberately does not do

It does not run provider calls merely because workflows exist. It does not write new Pionex historical data to R2, does not open the replacement holdout, does not train/promote a model, and does not activate live trading.

The workflows are control-plane entry points only; actual evidence is created only by a later reviewed `main` manual dispatch.
