# Qookey Crypto Autopilot

Cloud-first, exchange-agnostic crypto trading research and automation platform.

> **Current mode: PAPER-ONLY.** No real-money order path is authorized. `trade_plan_authorized=false` and `live_trading_authorized=false` remain mandatory. For the detailed current authority index, always read [`PROJECT_STATUS.md`](PROJECT_STATUS.md) first.

## Current authority snapshot — 2026-08-19

The repository has moved beyond the original V0.1 implementation baseline while preserving its scientific history:

- Pionex M1/M1A historical-data foundation: **PASS**.
- Cloudflare R2 historical storage and Binance 2025 pilot: **PASS**.
- Binance Funding V0.2 R2 materialization: **PASS** — 192/192 authorized object identities verified after write.
- Pionex ↔ Binance Equivalence V0.1: **definitive FAIL** — 45 pairs = 18 PASS / 18 REVIEW / 9 FAIL. The frozen result must not be regraded by changing thresholds or scope.
- `source_switch_authorized=false`; Binance evidence remains `provider=binance_usdm` and must never be relabeled as Pionex-native evidence.
- V0.5 Render Free / Frankfurt Binance public-metadata transport: **PASS**.
- V0.6 Render transport authority transition: **PASS**, while historical V0.2 Self-Hosted Mac authority remains preserved.
- V0.7 successor Render metadata-capture protocol: **PREPARED / EXECUTION_NOT_AUTHORIZED**.
- V0.8 atomic execution-cutover contract: **PREPARED / EXECUTION_NOT_AUTHORIZED**.
- Replacement holdout `2026-08-28` through `2026-09-03`: **FROZEN_UNOPENED**; candle access and evaluation remain unauthorized.
- Metadata stability gate: **NOT_YET_RUN**.

The existing V0.2 `[self-hosted, macOS, ARM64]` workflow remains the only metadata-capture execution path already authorized until a separate versioned activation authority performs an atomic old/new cutover. V0.8 deliberately does **not** enable the Render relay, enable a successor schedule, disable the current V0.2 schedule, write metadata to R2, or access the holdout.

## FREE-ONLY cloud policy

The current cloud policy is frozen in [`config/cloud_free_tier_policy_v0_1.json`](config/cloud_free_tier_policy_v0_1.json):

- monthly project budget: **0 USD**;
- no paid fallback, automatic subscription change, or payment-method upgrade path;
- Cloudflare Containers are retired for this project because they require Workers Paid;
- Koyeb V0.4 is superseded and is not a current transport candidate;
- the current Mac-independent Binance public-metadata transport is the existing **Render Free / Frankfurt** web service;
- future metadata R2 writes must pass the FREE-ONLY operational 8 GB hard-stop/headroom gate first;
- Render must never receive R2 credentials.

## V0.1 strategy scope

V0.1 remains **research + backtest + paper trading only**. Live trading is intentionally disabled until explicit safety gates are passed.

Primary execution target: **Pionex perpetual futures**. Future exchange adapters must plug into the same exchange interface without changing strategy or risk logic.

### SState Intraday Wave V0.1

- Universe: roughly 10–20 liquid perpetual markets
- 4H: SState market context
- 1H: trend/setup filter
- 15m: pullback/reclaim entry
- Direction: LONG-only for V0.1
- Frequency: 0–3 trades/day; never force a trade
- Default risk: 1% equity per trade
- Leverage cap: 3x, isolated-margin design target
- Daily loss gate: -3R disables new entries until next trading day

SState is treated as an upstream provider. Its validated core must not be rewritten by this repository.

## Architecture

```text
Provider-separated public market data
        |                    |
        |                    +--> Binance USD-M / Binance Vision research evidence
        |
        +--> Pionex native execution-target evidence
        |
        v
   Exchange Adapters -----> Historical Store / R2
        |
        +-----> SState Adapter
                   |
                   v
            Strategy Engine
                   |
                   v
               Risk Engine
                   |
                   v
              Paper Broker
                   |
                   v
              Performance

Future, separately gated only:
Paper Broker -> Private Execution Adapter
```

Current zero-cost infrastructure split:

- GitHub: source, CI, authority receipts, scheduled orchestration and validation jobs;
- Render Free / Frankfurt: successor Binance public-metadata transport leg only;
- Cloudflare R2 Standard Free: immutable historical/provider metadata storage under explicit write authority;
- GitHub Pages / static assets: read-only Traditional Chinese dashboard;
- Cloudflare Free services may be used only within the frozen FREE-ONLY policy and only where they are not transport-blocked.

## M1 historical data foundation

M1 adds public-data-only tools for discovering active Pionex PERP symbols, ranking a controlled USDT-PERP universe, deterministic Kline pagination for `15M` / `60M` / `4H`, and duplicate/order/gap/alignment/OHLCV integrity audits.

Select a current 15-symbol candidate universe:

```bash
python scripts/select_pionex_universe.py --target-size 15
```

Backfill an explicit historical range:

```bash
python scripts/backfill_pionex_history.py BTC_USDT_PERP 15M \
  --start 2026-01-01T00:00:00Z \
  --end 2026-08-01T00:00:00Z \
  --output /tmp/BTC_USDT_PERP-15M.json
```

Bulk historical data is not stored in GitHub; canonical storage evidence is kept in R2 under versioned authorities and receipts.

## Safety boundary

- Never commit Pionex/Binance API keys, relay tokens, Cloudflare tokens, R2 credentials, or other secrets.
- `.env.example` contains variable names only.
- A shared future `METADATA_RELAY_TOKEN` must be provisioned out of band in Render and GitHub Actions; its value must not be committed or pasted into issues/logs/chat.
- No martingale, loss-doubling, unlimited averaging down, cross-margin dependency, or liquidation-as-stop.
- Provider provenance remains explicit; provider splicing, silent interpolation and Pionex-native relabeling are forbidden.
- Render relay/successor scheduling must not be enabled before a separate atomic activation authority disables the old V0.2 scheduled path in the same cutover.
- No live order path is authorized.

## Quick start

Python 3.11+ recommended.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Fetch a public Pionex sample (no API key required):

```bash
python scripts/fetch_pionex_sample.py BTC_USDT_PERP 15M
```

## Authority and documentation

Read in this order for current work:

1. [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
2. [`AGENTS.md`](AGENTS.md)
3. current versioned protocol/config and receipt for the stage being changed
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
5. [`docs/STRATEGY_V0_1.md`](docs/STRATEGY_V0_1.md) and [`config/strategy_v0_1.json`](config/strategy_v0_1.json)

Historical receipts remain immutable evidence even when a later version supersedes their execution role.
