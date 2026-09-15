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

## REST/OpenAPI adapter

Toolkit V0.1 now has a dependency-free full-CPython HTTP adapter:

```bash
QOOKEY_TOOLKIT_API_TOKEN='replace-me' \
QOOKEY_TOOLKIT_HOST=127.0.0.1 \
python scripts/qookey_crypto_toolkit_http_v0_1.py
```

Available routes:

```text
GET  /healthz
GET  /openapi.json
GET  /v0/capabilities
POST /v0/indicators
POST /v0/strategy
POST /v0/risk
POST /v0/backtest
```

Protected POST routes use bearer authentication when `QOOKEY_TOOLKIT_API_TOKEN` is configured. The server refuses non-loopback exposure without that token. Request bodies are capped at 2 MB and CORS is disabled unless an explicit origin is configured.

The HTTP adapter delegates to the exact same Toolkit functions used by Python and CLI. It does not reimplement strategy logic.

## Cloud deployment layering

The prepared deployment layout is:

```text
Website / Telegram / other client
             ↓
Cloudflare edge gateway
  auth / request ID / size limits
             ↓
Full-CPython Toolkit API origin
             ↓
Qookey Crypto Toolkit
             ↓
Existing deterministic project core
```

Prepared infrastructure:

- `infra/cloudflare/qookey-toolkit-edge/` — thin Worker proxy only.
- `infra/render/qookey-toolkit-api/` — full-CPython origin container.
- `config/qookey_crypto_toolkit_api_v0_1.json` — machine-readable API/deployment policy.

The Cloudflare Worker intentionally has no provider credentials, R2 binding, holdout binding, or strategy logic. It separates a client-facing bearer token from the private origin bearer token.

The origin container copies only the Python modules needed for Toolkit execution and does not install the repository's cloud/history dependencies. This reduces deployment surface and prevents accidental R2 coupling.

## Interface decision

The layering is now:

```text
Existing crypto-autopilot core
        ↓
Qookey Crypto Toolkit
        ↓
Python / CLI / REST
        ↓
Cloudflare edge / website / Telegram / automation
```

MCP is intentionally deferred. A future MCP adapter, if reintroduced, must call the existing Toolkit and must not duplicate indicators, strategy, risk, or backtesting.

## Useful next integrations

After the HTTP path is stable, the most useful additions are:

- Telegram as a human command/report client over REST.
- Cloudflare Access or rate limiting before broad public exposure.
- Queues only when asynchronous/long-running tool jobs are introduced.
- Workflows only when durable multi-step jobs are introduced.
- NotebookLM remains a separate research-source adapter; browser profiles, cookies, Google sessions, CSRF tokens, and local NotebookLM credentials must never be committed.

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
