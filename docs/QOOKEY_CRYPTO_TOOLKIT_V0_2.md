# Qookey Crypto Toolkit V0.2

Status: `PREPARED_RESEARCH_ONLY`.

V0.2 is cloud-first. GitHub Actions remains the primary zero-local-setup interface, while a prepared REST/OpenAPI + Cloudflare edge + full-CPython origin layer is now available for future website, Telegram, and automation clients. The REST layer is implemented but **not deployed and not authorized for public exposure**. Python and CLI remain reusable internal runners. MCP remains deferred.

## Cloud research tools

- `validate_candles()` reuses the repository's audited `historical.audit_candles()` logic. It reports duplicate timestamps, out-of-order rows, gaps and missing-bar counts, interval misalignment, and invalid OHLCV. It never fills or repairs a gap.
- `stress_paper_backtest()` reruns the existing deterministic paper-only backtest under at most 64 named execution-cost scenarios. Only taker fee, slippage and conservative same-bar exit handling may be varied. Strategy parameters, plans, stops, targets and risk rules are not automatically mutated.
- `compare_backtests()` compares already-materialized Toolkit paper-backtest evidence. It reports descriptive extremes and deltas only; it does not choose, freeze, promote or authorize a strategy.
- `build_research_report()` creates a deterministic Markdown summary from validation, stress and/or comparison evidence. It makes no future-profitability claim.
- Existing V0.1 indicator, strategy, risk-sizing and paper-backtest tools remain available and backward compatible.

## GitHub Actions use

Use GitHub Actions for the primary cloud path:

1. Open **Actions**.
2. Select **Qookey Crypto Toolkit V0.2 Cloud**.
3. Choose **Run workflow** on `main`.
4. Select the tool command.
5. Provide a repository-relative JSON input path when the command needs one. `capabilities` needs no input file. `validate` and `indicators` also require an interval.
6. Download the generated `qookey-crypto-toolkit-v0-2-*` artifact from the workflow run.

The GitHub-hosted runner installs the constrained project runtime, executes the Toolkit, writes a secret-free output file, uploads it as an Actions artifact, and removes the disposable runner output. Direct R2 reads remain disabled because R2 access is a separate authority boundary.

## REST/OpenAPI adapter

The prepared HTTP adapter exposes the same deterministic V0.2 Toolkit functions; it does not reimplement strategy logic.

Public read-only routes:

```text
GET  /healthz
GET  /openapi.json
GET  /v0/capabilities
```

Protected research routes:

```text
POST /v0/validate
POST /v0/indicators
POST /v0/strategy
POST /v0/risk
POST /v0/backtest
POST /v0/stress
POST /v0/compare
POST /v0/report
```

Local loopback example:

```bash
QOOKEY_TOOLKIT_API_TOKEN='replace-me' \
QOOKEY_TOOLKIT_HOST=127.0.0.1 \
python scripts/qookey_crypto_toolkit_http_v0_2.py
```

The server refuses non-loopback binding without `QOOKEY_TOOLKIT_API_TOKEN`, caps request bodies at 2 MB, uses exact-origin CORS, emits `no-store`, and never logs Authorization headers or request bodies.

Machine-readable HTTP/deployment policy: `config/qookey_crypto_toolkit_api_v0_2.json`.

## Prepared cloud layering

```text
Website / Telegram / automation client
                ↓
Cloudflare edge gateway
 auth / exact CORS / size limit / request ID
                ↓
Full-CPython Toolkit V0.2 API origin
                ↓
Qookey Crypto Toolkit
                ↓
Existing deterministic project core
```

Prepared infrastructure:

- `infra/cloudflare/qookey-toolkit-edge/` — thin authenticated Worker proxy only.
- `infra/render/qookey-toolkit-api/` — minimal full-CPython origin container.
- `config/qookey_crypto_toolkit_api_v0_2.json` — API/deployment boundary.

The Worker contains no strategy logic, exchange credentials, R2 binding, or holdout binding. It requires an HTTPS origin, blocks upstream redirects, uses a client token distinct from the private origin token, and strips `set-cookie` / `location` from proxied responses.

The origin container copies project source plus the HTTP entry script and does not provision R2 credentials or exchange credentials.

## Internal CLI runner

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

Local use is optional, not required.

## Interface decision

- GitHub Actions: primary currently-authorized cloud execution interface.
- REST/OpenAPI: implemented and prepared, but deployment/public exposure remains unauthorized.
- Telegram: deferred until an authorized HTTP deployment exists; it should remain a thin client rather than own strategy logic.
- MCP: deferred. If later added, it must call the same Toolkit functions rather than duplicate indicators, strategy, risk, or backtesting.

## Safety boundary

All provider, R2, replacement holdout, source-switch, synthetic/interpolation, automatic strategy mutation, model promotion, formal trade-plan, real-money-order and live-trading authorities remain `false`.

This V0.2 REST work does not authorize automatic deployment, public exposure, secrets in Git, provider access, model promotion, trade plans, real-money orders, or live trading. A later deployment authority must explicitly bind exact service configuration, secrets, health validation, rollback, and exposure policy.
