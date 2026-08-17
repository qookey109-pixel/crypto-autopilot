# Architecture

## Design goal

Qookey Crypto Autopilot is cloud-first and exchange-agnostic. Pionex is the first exchange adapter, not the core architecture.

## Runtime layers

```text
Pionex / future exchanges
        |
        v
Exchange adapters
        |
        +--> Market data / historical data
        |
        +--> SState adapter (read-only upstream)
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
```

## Planned cloud deployment

- Cloudflare Pages: dashboard UI
- Cloudflare Workers: API, scheduler, lightweight strategy/risk runtime
- Durable Objects: live account/position state, order state, daily risk, kill switch
- D1: signals, decisions, orders, trades, P&L
- R2: historical candles, SState snapshots, model artifacts, backtests, reports
- GitHub Actions: tests, backtests, offline model/research jobs

The browser is a cockpit only. Closing the website must not stop the bot once cloud runtime is introduced.

## Exchange boundary

Strategy and risk code must not call Pionex-specific APIs directly. Exchange-specific behavior belongs under `src/crypto_autopilot/exchanges/`. A future MAX adapter should be able to implement the same boundary without rewriting strategy logic.

## Authority rules

- Backtest/paper state is internal to this project.
- When live trading is eventually enabled, the exchange is authoritative for actual balances, positions, orders, and fills.
- Internal state must reconcile against the exchange after restart or API uncertainty.
- No LLM may bypass deterministic risk or kill-switch rules.
