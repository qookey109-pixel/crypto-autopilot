# Agent Instructions

## Source of truth

Read these first:

1. `PROJECT_STATUS.md`
2. `README.md`
3. `docs/STRATEGY_V0_1.md`
4. `config/strategy_v0_1.json`

## Non-negotiable boundaries

- Do not enable live trading in V0.1.
- Do not add or commit secrets.
- Do not rewrite the validated SState core; integrate through the adapter only.
- Pionex is the first exchange, not the architecture.
- Keep strategy, risk, portfolio, persistence and exchange execution separable.
- Do not force a fixed number of daily trades.
- Do not introduce martingale, loss-doubling or unlimited averaging down.
- Do not increase leverage above the configured cap without a new version and explicit validation.

## Change discipline

- Preserve passing tests.
- Add tests for behavior changes.
- Record strategy parameter changes in configuration and status docs.
- Treat backtest results as evidence, not proof of future profitability.
- Prefer deterministic fixtures for tests.
