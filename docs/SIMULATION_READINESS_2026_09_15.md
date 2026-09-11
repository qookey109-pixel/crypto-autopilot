# Simulation Readiness — 2026-09-15

Status: **CONSOLIDATED INTEGRATION PREPARED — NOT YET ON `main` — NOT FULL_SIMULATION_READY**

This document is the short operational map for the 2026-09-15 paper/simulation target. Historical receipts remain immutable evidence; Draft PRs do not become Repository authority until reviewed merge.

## Safety boundary

The target is simulation/paper execution only.

Not authorized:

- real-money orders or live trading;
- private Pionex account API access;
- replacement-holdout access;
- source switching;
- automatic model promotion;
- automatic historical-materialization schedules.

The prepared Pionex control-plane workflows are manual `workflow_dispatch` only and use public market-data endpoints without an API key.

## Evidence already frozen into this integration path

The valid post-merge Pionex V0.2 bounded pilot report for run `34513815680` is included as evidence.

It proves one exact `BTC_USDT_PERP` capacity sample:

- `15M`: 2,592 rows;
- `60M`: 648 rows;
- `4H`: 162 rows;
- window: 2026-08-01 inclusive through 2026-08-28 exclusive UTC;
- R2 publication completed with latest-pointer-last semantics;
- replacement holdout remained unopened.

It is a 27-day bounded sample, not a full-history or profitability claim.

## Integrated simulation engine P0

Simulation Readiness V0.3 is now included in this consolidated branch.

Execution correctness includes:

- non-finite risk/backtest values fail closed;
- gap-through-stop exits use the first available candle open rather than an unreachable stop price;
- kill switch closes an open position and blocks later entries;
- maximum holding time is supported;
- next-bar-only entry remains causal;
- fees, slippage, risk and portfolio accounting remain deterministic.

The simulation-only candle adapter accepts only the exact V0.2 sample contract and requires receipt-bound Parquet SHA-256 and byte-size agreement before decoding.

It derives LONG simulation plans causally from:

- `4H` trend context;
- `60M` setup;
- `15M` pullback/reclaim/breakout/volume entry evidence.

It does not fabricate SState probability/sample values and does not modify formal Strategy V0.1.

`PIPELINE_PASS_KLINE_ONLY` remains weaker than `FULL_SIMULATION_READY` because provider-native historical funding evidence has not yet been captured/admitted.

## Manual public control plane

### 1. Historical Reach Discovery V0.3

Workflow: `pionex-historical-reach-v0-3.yml`

Measures public Pionex K-line reach for `BTC_USDT_PERP` at:

- `15M`;
- `60M`;
- `4H`;
- `1D`;
- `1W`.

Each interval stops at either a proven provider-earliest boundary or the documented 10,000-record ceiling. `1Y` is not provider-native and remains a later derivation from validated `1D` evidence.

BTC reach is provider-reference evidence only. Every other market must independently prove its own earliest available boundary during later materialization.

### 2. Pionex Research Universe 150+ V0.1

Workflow: `pionex-research-universe-v0-1.yml`

Exactly three public snapshot requests feed the deterministic selector:

1. live PERP symbols;
2. PERP tickers;
3. PERP book tickers.

The selector requires at least 150 quality-valid markets and preserves:

- 100 Pionex-liquidity-ranked crypto-core markets;
- quality-valid explicit meme-watchlist matches;
- quality-valid tokenized-equity / fund / metals registry matches;
- deterministic fill from remaining crypto when needed.

This is not a claim of global market-cap Top 100.

### 3. Tiered 150+ history planner V0.1

The deterministic planner performs no provider execution.

Profiles:

- `FULL_INTRADAY`: at most 30 markets → `15M / 60M / 4H / 1D / 1W`;
- `MULTISCALE_RESEARCH`: remaining core/meme markets → `60M / 4H / 1D / 1W`;
- `BREADTH_BACKGROUND`: remaining selected markets → `1D / 1W`.

Each market/interval remains capped at 10,000 records / 20 data pages plus one optional boundary probe until a later materialization authority defines a narrower reviewed range.

### 4. Pionex Funding History V0.1

Workflow: `pionex-funding-history-v0-1.yml`

Purpose: obtain provider-native funding evidence for the same BTC V0.2 window.

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

A PASS capture remains evidence only. It does not automatically authorize production-data admission into the simulator.

## Shortest remaining path to the 9/15 simulation test

1. Review/merge the consolidated code path; no automatic merge is authorized here.
2. Manually run Historical Reach Discovery and freeze its secret-free PASS/FAIL report.
3. Manually run the 150+ Universe Snapshot and freeze its secret-free PASS/FAIL report.
4. Feed reviewed reach + universe reports into the deterministic 150+ history planner.
5. Manually run bounded Pionex Funding History and freeze its report.
6. Create/review the exact historical-materialization and production-data-admission authority based on measured reach and capacity, not guessed years.
7. Admit exact K-line + funding evidence to Simulation Readiness V0.3.
8. Run historical/paper simulation and emit trade ledger, PnL, drawdown, fees, slippage, funding, kill-switch behavior and readiness report.
9. Declare `READY` only if the final gate passes; otherwise declare `NOT_READY` with explicit blockers.

## Current blockers

- New public workflows are not executable from Repository authority until reviewed onto `main`.
- Historical reach evidence for the five native intervals has not yet been produced.
- The real 150+ Pionex universe snapshot has not yet been produced.
- Pionex-native historical funding evidence has not yet been produced.
- Large 150+ historical materialization remains intentionally unauthorized until reach/capacity evidence exists.
- Production V0.2 K-line + funding data admission into the simulator remains separately reviewable.

These blockers are execution/evidence gates, not permission to fabricate or silently substitute data.
