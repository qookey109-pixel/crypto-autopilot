# Resource Hub Descriptive Context Envelope V0.1

Status: `PREPARED_RESEARCH_ONLY`

## Purpose

This is the first implementation step allowed by the reviewed World Monitor evaluation:

`research/receipts/2026-09-15-resource-hub-world-monitor-evaluation-v0-1.json`

The goal is **not** to connect World Monitor. The goal is to independently define the smallest fail-closed contract that external geopolitical and macro context would have to satisfy before a future integration could even be considered.

V0.1 accepts **synthetic fixtures only**.

It has no HTTP client, MCP client, SDK dependency, API key, OAuth flow, provider access, R2 access, frozen-holdout access, scheduler, broker, order path, or live-trading path.

## Contract

Policy:

`config/resource_hub_descriptive_context_v0_1.json`

Implementation:

`src/crypto_autopilot/toolkit/descriptive_context_v0_1.py`

A valid synthetic payload contains exactly:

- `source`
- `context_type`
- `observed_at`
- `cached_at`
- `stale`
- `summary`
- `severity`
- `provenance`

The frozen descriptive context types are:

- `geopolitical_event`
- `supply_chain_disruption`
- `sanctions_context`
- `energy_context`
- `cyber_context`
- `disaster_context`
- `market_stress_context`

These labels describe the environment. They do not predict BTC, ETH, altcoin, USD-M perpetual, or Pionex price direction.

## Freshness and time safety

The envelope requires timezone-aware timestamps and rejects:

- `observed_at > cached_at`;
- timestamps materially in the future;
- cache age beyond the frozen one-hour budget;
- observation age beyond the frozen six-hour budget;
- `stale = true`.

`as_of` is supplied explicitly by the caller rather than read from the system clock, keeping fixture tests deterministic and replayable.

## Provenance

V0.1 requires one to eight provenance entries. Every entry must have exactly:

- `source_name`
- `source_url`

URLs must use HTTPS and duplicate URLs are rejected.

This is intentionally narrower than World Monitor's full provenance/credibility model. No upstream AGPL code is copied or imported. The implementation is independently authored from the reviewed contract-level ideas.

## Directional-language firewall

The summary is bounded and normalized, but it is not interpreted into a trading recommendation.

V0.1 rejects explicit action/direction language such as:

- buy / sell;
- go long / go short;
- bullish / bearish;
- entry, stop-loss, take-profit;
- price target / target return;
- position size / leverage;
- trade plan;
- risk-on / risk-off.

The payload schema is exact. Extra fields such as `expected_return`, `position`, `target_price`, or other undeclared values are rejected rather than silently carried through.

## Output boundary

A successful result always reports:

- `status = RESEARCH_ONLY`
- `decision = DESCRIPTIVE_CONTEXT_ONLY`
- `directional_signal = null`
- `strategy_eligible = false`
- `formal_backtest_eligible = false`
- `trade_plan_eligible = false`

Every authority flag remains `false`.

The envelope can therefore preserve a time-safe description such as “a shipping route interruption was reported near a major chokepoint” without converting that statement into “short BTC”, “risk-off”, a strategy parameter change, a model-promotion signal, or a trade plan.

## What V0.1 does not prove

Passing this contract does not prove:

- World Monitor API correctness or availability;
- causal influence on crypto returns;
- predictive value of CII, conflict, sanctions, energy, cyber, or supply-chain data;
- Binance/Pionex provider equivalence;
- permission to persist or redistribute third-party World Monitor data;
- strategy edge;
- formal backtest admission;
- model promotion;
- order or live-trading authority.

Any future live-source step requires a new reviewed version, explicit credential/network authority, source/terms review, and a separate point-in-time calibration plan. V0.1 itself remains synthetic and network-free.
