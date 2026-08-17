# Qookey Crypto Autopilot

Cloud-first, exchange-agnostic crypto trading research and automation platform.

## V0.1 scope

V0.1 is **research + backtest + paper trading only**. Live trading is intentionally disabled until explicit safety gates are passed.

Primary exchange: **Pionex perpetual futures**. Future exchange adapters (for example MAX) must plug into the same exchange interface without changing strategy or risk logic.

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
Pionex Public Market Data
          |
          v
   Exchange Adapter -----> Historical Store (later R2)
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

Future, gated path only:
Paper Broker -> Pionex Private Execution Adapter
```

Cloud target:

- GitHub: source, CI, backtests, model-training jobs
- Cloudflare Workers: API / scheduler / lightweight runtime
- Durable Objects: current account/position state and kill switch
- D1: signals, decisions, orders, trades, P&L
- R2: historical candles, SState snapshots, models, reports
- Cloudflare Pages: dashboard / Performance Center
- Pionex: market data and, only after safety approval, execution

## Safety boundary

- Never commit Pionex API keys, secrets, Cloudflare tokens, or credentials.
- `.env.example` contains variable names only.
- No martingale, loss-doubling, unlimited averaging down, cross-margin dependency, or liquidation-as-stop.
- No live order path is implemented/enabled in V0.1.
- When live execution is eventually introduced, exchange-reported order/position state is authoritative.

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

## Status

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/STRATEGY_V0_1.md`](docs/STRATEGY_V0_1.md).
