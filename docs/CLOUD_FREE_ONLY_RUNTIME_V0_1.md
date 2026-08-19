# Cloud FREE-ONLY Runtime V0.1

Status: **FROZEN DESIGN / $0 MONTHLY BUDGET**

## Decision

Qookey Crypto Autopilot uses a **FREE-ONLY** cloud runtime policy unless a later, explicit versioned authority changes it.

The project monthly cloud budget is `0 USD`. No workflow may automatically upgrade a Cloudflare plan, enable a paid fallback, or knowingly cross a project safety ceiling that could create usage-based charges.

This decision does not change any scientific/provider authority. It only constrains runtime and infrastructure choices.

## Current Cloudflare result

Cloudflare Container V0.3 diagnostic run `32246057672` reached Worker upload and Container image build, but Container application registration returned `Unauthorized`. The Binance probe was never reached.

The account is on the Cloudflare Free plan. Cloudflare Containers are documented as Workers Paid-only, so this path is now `BLOCKED_FREE_PLAN_NO_RETRY` for this project. The diagnostic evidence is preserved; it is not rewritten as PASS.

Authority receipt:

`research/receipts/2026-08-19-provider-equivalence-v0-3-cloudflare-container-free-plan-blocked.json`

## Free architecture

```text
GitHub
  source / CI / tests / versioned authority
          |
          v
Cloudflare Workers Free
  cron entry / lightweight API / status endpoint
          |
          v
Cloudflare Workflows Free
  durable orchestration / retries / resumable steps
          |
          +------> Cloudflare Queues Free
          |          event buffering / retry / backpressure
          |
          +------> Cloudflare D1 Free
          |          slot state / audit index / budget snapshot
          |
          +------> Cloudflare R2 Standard Free
                     immutable evidence / parquet / receipts

Provider transport
  must have a separate ZERO-COST proof if Cloudflare Worker egress is blocked.
```

## Conservative FREE-ONLY ceilings

The exact machine-readable authority is:

`config/cloud_free_tier_policy_v0_1.json`

Project ceilings intentionally stay below published free limits to leave headroom for shared-account usage and delayed usage reporting.

- Workers: 75,000 requests/day; at most 4 Cron triggers; max 40 external subrequests/invocation.
- Workflows: 2,250 steps/day; 0.75 GB-month state; max 768 steps/instance.
- Queues: 7,500 operations/day; 24-hour retention.
- D1: 4,000,000 rows read/day; 75,000 rows written/day; 4 GB total storage.
- R2 Standard: 8 GB-month; 750,000 Class A/month; 7,500,000 Class B/month.

Approaching a project ceiling is a **STOP**, not an invitation to upgrade.

## Features disabled by default

- Cloudflare Containers: unavailable on Free for this project.
- R2 SQL: disabled until a separate zero-cost budget proof exists.
- R2 Data Catalog: disabled until a separate zero-cost budget proof exists.
- Durable Objects: not used in V0.1 free control plane unless a later need + budget proof justifies them.

## Provider transport boundary

Cloudflare control/data-plane services may be used even when provider transport is elsewhere.

The provider transport must not be silently changed merely to obtain a PASS. In particular:

- no proxy bypass;
- no endpoint substitution;
- no Binance API key bypass for public `exchangeInfo`;
- no provider splice;
- no provenance relabeling.

The V0.2 Self-Hosted Mac transport remains current authority until a separate zero-cost, Mac-independent transport is proven and a versioned authority transition is merged.

## Scientific/safety boundary

FREE-ONLY cloud migration does not authorize:

- replacement holdout candle access;
- source switch;
- Trade-Kline W1;
- Historical Universe membership;
- backtest admission;
- automatic trade plan;
- real-money orders;
- live trading.

The project remains **PAPER-ONLY**.
