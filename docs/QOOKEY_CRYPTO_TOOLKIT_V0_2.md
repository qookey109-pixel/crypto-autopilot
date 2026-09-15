# Qookey Crypto Toolkit V0.2

Status: `PREPARED_RESEARCH_ONLY`.

V0.2 extends the local Toolkit without adding REST, Telegram, MCP, provider access, R2 access, holdout access, promotion authority, or trading authority. V0.1 Python/CLI behavior remains compatible.

## New local research tools

- `validate_candles()` reuses the repository's audited `historical.audit_candles()` logic. It reports duplicate timestamps, out-of-order rows, gaps and missing-bar counts, interval misalignment, and invalid OHLCV. It never fills or repairs a gap.
- `stress_paper_backtest()` reruns the existing deterministic paper-only backtest under at most 64 named execution-cost scenarios. Only taker fee, slippage and conservative same-bar exit handling may be varied. Strategy parameters, plans, stops, targets and risk rules are not automatically mutated.
- `compare_backtests()` compares already-materialized Toolkit paper-backtest evidence. It reports descriptive extremes and deltas only; it does not choose, freeze, promote or authorize a strategy.
- `build_research_report()` creates a deterministic Markdown summary from validation, stress and/or comparison evidence. It makes no future-profitability claim.

## Direct use

Python imports are available from `crypto_autopilot.toolkit`.

The V0.2 CLI is:

```bash
python scripts/qookey_crypto_toolkit_v0_2.py capabilities
python scripts/qookey_crypto_toolkit_v0_2.py validate --input candles.json --interval 4h
python scripts/qookey_crypto_toolkit_v0_2.py indicators --input candles.json --interval 4h
python scripts/qookey_crypto_toolkit_v0_2.py strategy --input opportunity.json
python scripts/qookey_crypto_toolkit_v0_2.py risk --input risk.json
python scripts/qookey_crypto_toolkit_v0_2.py backtest --input backtest.json
python scripts/qookey_crypto_toolkit_v0_2.py stress --input stress.json
python scripts/qookey_crypto_toolkit_v0_2.py compare --input comparison.json
python scripts/qookey_crypto_toolkit_v0_2.py report --input report.json
```

Use `--input -` to read JSON from stdin.

## Stress input

`stress_paper_backtest()` expects the normal V0.1 backtest payload under `backtest` plus named scenarios:

```json
{
  "backtest": {"candles_by_symbol": {}, "plans": []},
  "scenarios": [
    {"name": "base", "taker_fee_bps": 5, "slippage_bps": 2},
    {"name": "cost-stress", "taker_fee_bps": 10, "slippage_bps": 8}
  ]
}
```

The tool deliberately rejects arbitrary scenario keys. It is an execution-assumption stress test, not an automatic optimizer.

## Comparison input

Comparison accepts at least two complete outputs previously produced by `run_paper_backtest()`:

```json
{
  "results": [
    {"label": "baseline", "result": {}},
    {"label": "candidate", "result": {}}
  ]
}
```

The first label is the delta baseline. `highest_return`, `lowest_drawdown` and `highest_profit_factor` are descriptive historical extrema, not a recommendation.

## Deferred interfaces

REST/API, Telegram and MCP are intentionally deferred. V0.2 is designed for local Python, CLI and repository-controlled GitHub Actions execution only.

## Safety boundary

All provider, R2, replacement holdout, source-switch, synthetic/interpolation, automatic strategy mutation, model promotion, formal trade-plan, real-money-order and live-trading authorities remain `false`.
