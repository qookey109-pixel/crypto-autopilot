# Paper Simulation Demo V0.1

## Purpose

This demo exercises the existing deterministic paper backtest lifecycle with an explicit,
synthetic set of LONG trade plans. It is a runnable smoke simulation, not a historical
strategy evaluation or a profitability claim.

## Run

```bash
PYTHONPATH=src python scripts/run_paper_simulation_demo.py \
  --output /tmp/paper-simulation-demo-v0-1.json
```

The report includes assumptions, trades, equity, costs, funding and explicit authority
flags. Omitting `--output` prints the same deterministic JSON without creating a file.

## Exercised behavior

- next-candle-open entry, never same-signal-candle fill;
- 1% equity risk sizing and 3x leverage cap;
- conservative stop/target handling;
- taker fees and adverse fill slippage;
- supplied positive and negative funding observations;
- target, stop and end-of-data exits;
- event and equity accounting.

## Boundary

The fixture does not auto-generate trade plans, call a provider, construct an R2 client,
read or write R2, access a holdout, or submit an exchange order. The result must not be
presented as real market performance. Historical strategy replay remains blocked until
the repository separately freezes the undefined entry/stop semantics and grants the
required data/backtest authority.
