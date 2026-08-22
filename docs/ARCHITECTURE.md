# Architecture

## Design goal

Qookey Crypto Autopilot is an exchange-agnostic research/automation platform. Pionex is the current execution target and provenance authority for Pionex-native evidence, not the core architecture.

Current mode is **PAPER-ONLY**. No private execution or real-money order path is authorized.

## Logical research stack

```text
Provider-separated public market data
        |                     |
        |                     +--> Binance USD-M / Binance Vision research evidence
        |
        +--> Pionex native execution-target evidence
        |
        v
Exchange adapters -----> Historical / metadata store (R2)
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

Provider identity is part of the data contract. Binance evidence must never be relabeled as Pionex-native evidence, and provider splicing/source switching requires separate authority.

## Current zero-cost infrastructure

The current deployed/repository architecture is:

- **GitHub repository** — source code, versioned configs/receipts and formal authority.
- **GitHub Actions** — CI, validation, offline research and the versioned V0.10 metadata-capture scheduler.
- **Render Free / Frankfurt** — authenticated transport for the Binance public metadata leg only.
- **Cloudflare R2 Standard Free** — immutable historical/provider metadata storage under explicit write authorities.
- **GitHub Pages** — read-only Traditional Chinese dashboard; it is a normalized view and never authority.

The project runtime budget is `0 USD/month`. Render must never receive R2 credentials.

Cloudflare Containers and Koyeb are historical/superseded transport experiments and are not current runtime components. Earlier plans that mentioned Cloudflare Workers, Durable Objects or D1 are **future design possibilities only**; they are not current authority and must not be introduced as paid/runtime dependencies without a separately versioned decision.

## Current metadata authority path

```text
GitHub Actions V0.10 scheduler
        |
        +--> Pionex public metadata HTTPS
        |
        +--> authenticated Render Free Frankfurt relay
                 |
                 +--> Binance USD-M public exchangeInfo
        |
        v
fresh 8 GB R2 headroom gate
        |
        v
immutable run-scoped metadata objects
(receipt written last + SHA-256 readback)
```

The V0.10 path is authorized only inside the frozen metadata window. Historical V0.2 self-hosted scheduled execution is retired and is not an automatic fallback.

## Pionex public paper-training path

```text
GitHub Actions (hourly, bounded before 2026-08-27 UTC)
  -> Pionex public futures market endpoints only
  -> audited 15M / 60M / 4H / 8H / 1D closed candles
  -> causal technical + volatility + market-state features
  -> fixed, versioned candidate gates (no parameter search)
  -> deterministic Repository Paper Broker
  -> run-scoped artifact + secret-free forward-state cache
  -> read-only GitHub Pages projection
  -> up to three Pionex Demo samples for manual review only
```

This path is independent of the frozen V0.10 production-critical workflow. It
does not read or write R2, inspect the replacement holdout, switch providers,
call private Pionex endpoints or create any exchange order. Current order-book,
recent-trade, funding, basis and open-interest features describe only the
forward run state; they are not injected into historical replay bars.

V0.11 metadata-stability evaluator rules are frozen before production evidence is read, but production R2 evaluation remains hard-disabled. Its prepared authority does not construct R2 clients, read production receipts, call providers/Render, or access the replacement holdout.

## Workflow lifecycle

A workflow that produced frozen authority evidence is not automatically a reusable production tool. Once its execution role is superseded or complete, keep the filename/history but retire external side effects:

- no schedule;
- no push-triggered production execution;
- no manual production rerun;
- no provider/R2 secret binding;
- no self-hosted runner requirement;
- validate the frozen receipt/config instead.

Reactivation requires a new versioned authority rather than silently editing a historical workflow back into service.

## Exchange boundary

Strategy and risk code must not call Pionex-specific APIs directly. Exchange-specific behavior belongs under `src/crypto_autopilot/exchanges/`. Future adapters must implement the same boundary without rewriting strategy logic.

## Authority rules

- Repository `main` plus current versioned configs/receipts is formal project authority.
- Historical receipts remain immutable even when their execution role is superseded.
- Dashboard state is never authority.
- Replacement holdout remains `FROZEN_UNOPENED` until a separate holdout-access authority exists.
- No LLM or runtime may bypass deterministic risk, provenance, storage, authority or kill-switch rules.
- If live trading is ever separately authorized, the exchange becomes authoritative for actual balances, positions, orders and fills, and internal state must reconcile after restart/API uncertainty.

## Research governance layer V0.1

Offline research may use the separate governance layer in
`docs/RESEARCH_GOVERNANCE_V0_1.md`:

```text
lineage manifest → partition integrity → immutable experiment registry
                                      ↘ bounded resource-aware ordering
```

This layer records input/config/environment fingerprints and compares only
compatible runs. It has no provider, R2, holdout, trade-plan, promotion or
deployment authority. The V0.10 production-critical path and the paper-only
boundary remain unchanged.
