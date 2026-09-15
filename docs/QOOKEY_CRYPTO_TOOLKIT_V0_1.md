# Qookey Crypto Toolkit V0.1

Status: `PREPARED_RESEARCH_ONLY`.

This toolkit is a stable research-facing facade over existing `crypto-autopilot` core logic. It does not replace the project architecture and it does not make MCP a core dependency.

## Design

The core package is `crypto_autopilot.toolkit`. It exposes JSON-compatible wrappers around existing deterministic research logic:

- `get_indicators()` uses the existing audited technical indicator engine.
- `evaluate_strategy()` uses the existing deterministic V0.1 strategy gate.
- `size_long_trade_tool()` uses the existing risk-sizing engine.
- `run_paper_backtest()` uses the existing deterministic paper-only backtest engine.
- `list_capabilities()` publishes a machine-readable capability and safety boundary manifest.

All Toolkit V0.1 tools are local and side-effect free. They do not fetch provider data, construct an R2 client, access holdout data, mutate strategy authority, promote models, construct a formal trade plan, place real-money orders, or enable live trading.

## Direct use without MCP

The Python package can be imported directly:

```python
from crypto_autopilot.toolkit import get_indicators

result = get_indicators(candles, interval="4h")
```

The CLI provides the same contract without an AI client:

```bash
python scripts/qookey_crypto_toolkit_v0_1.py capabilities
python scripts/qookey_crypto_toolkit_v0_1.py indicators --input candles.json --interval 4h
python scripts/qookey_crypto_toolkit_v0_1.py strategy --input opportunity.json
python scripts/qookey_crypto_toolkit_v0_1.py risk --input risk.json
python scripts/qookey_crypto_toolkit_v0_1.py backtest --input backtest.json
```

Use `--input -` to read JSON from stdin.

## Interface decision

MCP is optional. The recommended layering is:

```text
Existing crypto-autopilot core
        ↓
Qookey Crypto Toolkit
        ↓
Python / CLI / REST / Telegram / MCP
```

Choose the interface by caller:

- Python: internal scripts, notebooks, GitHub Actions, tests.
- CLI: local automation, shell pipelines, Codex terminal workflows.
- REST/OpenAPI: websites, Telegram bots, Render/Cloudflare services, or clients that are not running inside Python.
- MCP: AI clients that should discover tool schemas and invoke tools directly.
- Telegram: human command/report interface; it should normally call the REST or Python toolkit rather than contain strategy logic itself.

A future MCP adapter should call `crypto_autopilot.toolkit` and must not reimplement indicators, strategy, risk, or backtesting.

## Recommended next adapters

The next generally useful adapter is a small read-only REST/OpenAPI service because it can serve a website, Telegram, and other automation at the same time. MCP can then be added as a thin adapter when direct AI tool discovery provides enough value.

NotebookLM remains a separate research-source adapter. Browser profiles, cookies, Google sessions, CSRF tokens, and local NotebookLM credentials must never be committed to this repository.

## Safety boundary

Toolkit V0.1 grants no new authority. In particular, all of the following remain false:

- provider access
- R2 access
- replacement holdout access
- source switching
- synthetic/interpolated candles
- automatic strategy mutation
- automatic model promotion
- formal trade plans
- real-money orders
- live trading

Backtest output remains research evidence, not evidence of future profitability.
