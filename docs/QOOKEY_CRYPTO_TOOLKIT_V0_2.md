# Qookey Crypto Toolkit V0.2

Status: `PREPARED_RESEARCH_ONLY`.

V0.2 is cloud-first. The intended user path is GitHub Actions from the browser; no Mac-local execution is required. The Python package and CLI remain as internal/reusable runners so the same deterministic logic can execute inside GitHub-hosted runners. REST, Telegram, MCP, provider access, R2 access, holdout access, promotion authority, and trading authority remain outside this version.

## Cloud research tools

- `validate_candles()` reuses the repository's audited `historical.audit_candles()` logic. It reports duplicate timestamps, out-of-order rows, gaps and missing-bar counts, interval misalignment, and invalid OHLCV. It never fills or repairs a gap.
- `stress_paper_backtest()` reruns the existing deterministic paper-only backtest under at most 64 named execution-cost scenarios. Only taker fee, slippage and conservative same-bar exit handling may be varied. Strategy parameters, plans, stops, targets and risk rules are not automatically mutated.
- `compare_backtests()` compares already-materialized Toolkit paper-backtest evidence. It reports descriptive extremes and deltas only; it does not choose, freeze, promote or authorize a strategy.
- `build_research_report()` creates a deterministic Markdown summary from validation, stress and/or comparison evidence. It makes no future-profitability claim.
- Existing V0.1 indicator, strategy, risk-sizing and paper-backtest tools remain available through the same cloud runner.

## Browser-first use

After this PR is merged, use GitHub:

1. Open **Actions**.
2. Select **Qookey Crypto Toolkit V0.2 Cloud**.
3. Choose **Run workflow** on `main`.
4. Select the tool command.
5. Provide a repository-relative JSON input path when the command needs one. `capabilities` needs no input file. `validate` and `indicators` also require an interval.
6. Download the generated `qookey-crypto-toolkit-v0-2-*` artifact from the workflow run.

The GitHub-hosted runner installs the constrained project runtime, executes the Toolkit, writes a secret-free output file, uploads it as an Actions artifact, and removes the disposable runner output. Your Mac does not need Python, the repository checkout, or a local Toolkit process.

V0.2 intentionally accepts repository-controlled JSON input only. Direct R2 reads remain disabled because R2 access is a separate authority boundary. Large-dataset/R2 input can be added later as an explicitly reviewed cloud extension without changing the Toolkit's research-only semantics.

## Internal runner

The cloud workflow calls the same deterministic CLI used by tests and automation:

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

This CLI is an implementation detail for cloud/repository automation; local use is optional, not required.

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

REST/API, Telegram and MCP remain intentionally deferred. GitHub Actions is the V0.2 cloud execution interface. No public HTTP service is required.

## Safety boundary

All provider, R2, replacement holdout, source-switch, synthetic/interpolation, automatic strategy mutation, model promotion, formal trade-plan, real-money-order and live-trading authorities remain `false`.
