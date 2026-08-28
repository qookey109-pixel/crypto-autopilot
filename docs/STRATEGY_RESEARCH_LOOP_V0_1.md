# Strategy Research Loop V0.1

Status: **PREPARED RESEARCH-ONLY / SYNTHETIC FIXTURES ONLY**

## Outcome

This version unifies three previously separate research concerns behind one
project-native contract:

```text
bounded candidate registry
  -> complete UPDATE family + disjoint VALIDATION evidence
  -> Strategy Edge Validation V0.1
  -> cost-complete Repository paper ledger audit
  -> human review eligibility only
```

It adapts useful concepts from strategy-discovery and trading-journal tools
without installing an external package, copying third-party code, creating a
second broker or introducing another governance system.

## Bounded strategy discovery

The frozen registry contains 120 deterministic hypotheses across:

- trend-following;
- mean-reversion;
- breakout;
- volume-flow;
- intraday, multiday and swing horizons.

Every candidate binds its family, horizon and parameters to a canonical
SHA-256. The complete ordered registry has a second SHA-256 and a hard global
cap of 4,096 candidates. V0.1 only prepares this registry: it does not fetch
data, materialize returns, select a winner or generate a trade plan.

The registry must exactly match the trial family supplied to Strategy Edge
Validation V0.1. This prevents a failed or omitted trial from disappearing
after the result is known.

## Paper performance audit

The audit accepts only a complete, ordered, single-currency
`SYNTHETIC_FIXTURE` ledger with explicit:

- symbol, direction, entry time and exit time;
- gross PnL, fees, funding and observed slippage cost;
- net PnL and initial risk;
- selected candidate, registry and edge-input fingerprints;
- zero provider, R2, holdout and trading authority.

The existing Repository `BacktestResult` can be adapted with
`paper_ledger_from_backtest_result`. This is an evidence adapter, not a new
broker. The current governed backtest is LONG-only, so the adapter records
`LONG` explicitly rather than inventing a SHORT result.

Repository backtest fill prices already contain slippage, so the audit retains
the explicit slippage amount for review but does not subtract it a second time.
It verifies `net = gross - fees - funding` for every record.

Metrics include expectancy in USD and R, payoff ratio, profit factor,
trade-level Sharpe/Sortino in R, actual maximum drawdown, consecutive losses,
winner concentration, holding duration and total fees/funding/slippage.

A deterministic stationary-bootstrap Monte Carlo resamples realized
R-multiples and reports ruin probability, final-equity percentiles and the 95th
percentile maximum drawdown. It is a fragility diagnostic, not a forecast.

Audit states are:

- `ACCEPTABLE_FOR_CONTINUED_PAPER_RESEARCH`;
- `FRAGILE_REVIEW_REQUIRED`;
- `INSUFFICIENT_SAMPLE`.

None promotes a strategy.

## Composition and fail-closed lineage

The final composition requires exact agreement among registry, edge input,
edge report and paper audit for candidate order, registry SHA, provider,
selected candidate and edge-input fingerprint. It also requires Strategy Edge
Validation `PASS`.

Outcomes are:

- `REJECT` for lineage mismatch or Edge failure;
- `RESEARCH_REVIEW_REQUIRED` for paper evidence that is incomplete or fragile;
- `EVIDENCE_READY_FOR_HUMAN_REVIEW` only when all evidence matches and passes.

The last state still grants zero model-promotion or trading authority.

## CLI

The one CLI has no network, output-file, broker or cloud-storage option:

```bash
PYTHONPATH=src python scripts/run_strategy_research_loop.py registry

PYTHONPATH=src python scripts/run_strategy_research_loop.py audit \
  --ledger /tmp/paper-ledger.json

PYTHONPATH=src python scripts/run_strategy_research_loop.py compose \
  --edge-input /tmp/edge-input.json \
  --edge-report /tmp/edge-report.json \
  --ledger /tmp/paper-ledger.json
```

Malformed or rejected evidence is printed as JSON and exits with status 2.

## External influences and provenance

The design uses concepts described by:

- Capafy Strategy Discovery Lab: bounded strategy search, honest
  out-of-sample survival and anti-overfitting reporting;
- `mars-tw/anti-gambling-trader-tw`: cost-complete trade records,
  expectancy/profit factor/drawdown/concentration review and Monte Carlo risk.

No Capafy package was installed and no source code was copied from either
project. The implementation is independent and keeps Repository authority,
SState, risk, backtest and exchange boundaries intact.

## Current authority boundary

- V0.10 production-critical path: unchanged.
- SState core: unchanged; adapter only.
- Production/provider/R2/holdout access: unauthorized.
- Candidate execution and production return evaluation: unauthorized.
- Workflow and schedule: absent.
- Model promotion, trade plans, real-money orders and live trading:
  unauthorized.
