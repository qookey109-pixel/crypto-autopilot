# TradingAgents Research Challenger V0.1

## Status

`PREPARED_RESEARCH_ONLY`

This integration adds a fail-closed adapter for secret-free output from
`TauricResearch/TradingAgents` v0.4.0. It does not install or vendor the upstream
framework and does not authorize an LLM call, provider request, schedule, R2
operation, holdout access, strategy change, trade plan or order.

## Position in the project

```text
Pionex candidate universe + provider-separated verified data
                         |
                         v
             TradingAgents external research run
                         |
                         v
        secret-free point-in-time candidate JSON
                         |
                         v
       TradingAgents Research Challenger adapter
                         |
                         v
        existing Research Context (authority=false)
                         |
                         v
        comparable evaluation / human review only
```

The upstream five-tier rating is descriptive challenger evidence. It cannot
replace the canonical strategy, Risk Engine or Paper Broker, and it cannot be
added to another score without a separately reviewed evaluation contract.

## Input envelope

The caller must export a JSON object with schema
`tradingagents-research-candidate-v0.1`. Required fields are:

- exact upstream repository, release and 40-character commit SHA;
- project canonical symbol plus the upstream ticker;
- declared upstream data provider;
- analysis date, decision timestamp and data cutoff timestamp;
- one of `BUY`, `OVERWEIGHT`, `HOLD`, `UNDERWEIGHT`, `SELL`;
- market, bull, bear, investment-plan, risk and final-decision reports;
- HTTPS evidence URLs;
- `point_in_time_verified=true`;
- explicit false values for holdout, source-switch, trade-plan, real-money and
  live-trading authority.

The adapter rejects future decisions, future data cutoffs, universe mismatch,
provider mismatch, secret-like fields, missing reports and protected authority.
It retains only report SHA-256 digests in normalized evidence, not the upstream
prose.

## Activation gate

Running TradingAgents automatically requires a successor authority that names:

1. the pinned upstream commit and dependency lock;
2. the exact Pionex-only candidate mapping and allowed data providers;
3. point-in-time evidence rules for prices, news and macro inputs;
4. model provider, model IDs, token and FREE-ONLY budget;
5. secret boundary and secret-free artifact contract;
6. cadence, concurrency, retry and maximum symbols per run;
7. a preregistered comparison against the current deterministic baseline.

Until then, only offline adapter validation is active engineering capability.
