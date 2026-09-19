# External Capability Registry V0.1

Status date: 2026-09-19

Status: **CANDIDATE REGISTRY ONLY / NO INSTALL / NO RUNTIME**

## Purpose

MCP.so is useful as a broad discovery catalog, but catalog presence is not
execution authority.

External Capability Registry V0.1 converts reviewed MCP candidates into a
small, exact-source inventory for Crypto Autopilot. Every entry is bound to an
exact public repository commit and remains:

`CANDIDATE / REVIEW_REQUIRED / production_eligible=false`

This implements the lifecycle previously anticipated by Resource Hub Supply
Chain:

```text
DISCOVERED
    ↓
CANDIDATE
    ↓
EVALUATED
    ↓
APPROVED
    ↓
ACTIVE
    ↓
DEPRECATED
```

V0.1 stops at **CANDIDATE**.


## Downstream evaluation index — 2026-09-19

The registry JSON remains intentionally candidate-only. The entries below are
**separate downstream evaluation receipts**; they do not silently promote a
candidate to APPROVED or ACTIVE.

| Capability | Evaluation outcome | Retained scope |
|---|---|---|
| `crypto_market_data_mcp` | Evaluated; runtime not approved | Prefetched derivatives-context contract reference |
| `agentfeed` | Evaluated; runtime not approved | Liquidation tape quality and side-semantics reference |
| `tradingcalc_mcp` | Evaluated; runtime not approved | Remote risk-formula challenger reference |
| `tradingview_mcp` | Evaluated; runtime not approved | Technical/backtest challenger reference |
| `depthy_mcp` | Evaluated; runtime not approved | Hyperliquid microstructure provider challenger |
| `0xarchive_mcp` | Evaluated; runtime not approved | Historical/data-quality challenger |
| `telegram_mcp` | Evaluated; not selected as default transport | Reference only; provider-neutral operator contract preferred |
| `cloudflare_mcp` | Evaluated; runtime not approved | Read-only observability/build/audit allowlist if needed |
| `github_official_mcp` | Evaluated; runtime not approved | Read-only repo/PR/Actions diagnostics if needed |
| `github_actions_mcp` | Evaluated; redundant, not selected | Prefer official GitHub MCP read-only Actions surface |

Evidence lives under `research/receipts/2026-09-19-*-evaluation-v0-1.json`
and the corresponding evaluation documents in `docs/`.

### Convergence rule

Do not re-evaluate or integrate one of these candidates merely because it is
still labeled `CANDIDATE / REVIEW_REQUIRED` in the V0.1 inventory.

Re-open a candidate only when at least one of these is true:

- the project has a concrete capability gap;
- the pinned upstream architecture materially changes;
- a new exact upstream commit is intentionally proposed;
- a separate authority explicitly opens the required runtime/network/secret
  boundary.

This keeps the registry useful as provenance inventory without turning every
discovered MCP server into a project dependency.

## Registered candidates

### Market data and microstructure

- **Crypto Market Data MCP** — multi-exchange public market data; candidate
  source for funding, open interest, long/short ratio and cross-exchange
  context.
- **AgentFeed** — liquidation tape, cascade and positioning research candidate.
  It uses x402 paid calls, so wallet/payment authority remains closed.
- **Depthy MCP** — Hyperliquid order-book/liquidation context plus prediction
  market context; credentialed remote dependency.
- **0xArchive MCP** — historical/realtime Hyperliquid, Lighter and HIP-3 market
  data candidate with explicit data-quality surfaces.

### Risk and strategy research challengers

- **Tradingcalc MCP** — deterministic PnL, liquidation, position-sizing,
  funding and risk calculation cross-check candidate. It must not replace
  Crypto Autopilot Risk authority merely because an upstream workflow emits a
  verdict.
- **TradingView MCP** — technical screener/backtest challenger. Its indicator,
  rating or strategy output cannot directly become Strategy Router authority.

### Operator and infrastructure candidates

- **Telegram MCP** — future notification / operator-command transport. Upstream
  write tools exist, so V0.1 grants no Telegram session or send authority.
- **Cloudflare MCP** — future infrastructure inspection/operations candidate.
  No Cloudflare credential or resource mutation is authorized.
- **GitHub Official MCP Server** — future repository-agent interface. Existing
  project GitHub governance remains authoritative; this candidate adds no repo
  mutation authority.
- **GitHub Actions MCP** — future workflow observability/control candidate. No
  dispatch, cancel, rerun or workflow mutation is authorized.

## Source review

Every candidate records:

- repository owner/name;
- actual default branch at review time;
- exact 40-character commit SHA;
- verified license;
- archived state;
- coarse capability list;
- credential/payment/network requirements;
- write/payment/secret risk flags.

The registry does not vendor upstream source code.

Upstream repositories remain third-party dependencies and must be re-reviewed
before a commit pin can change.

## Why this is separate from External Market Context V0.1

External Market Context is a data-shape layer for six already-selected context
sources.

External Capability Registry is wider. It includes:

- raw market-data candidates;
- historical-data candidates;
- deterministic risk challengers;
- technical research challengers;
- notification tools;
- cloud infrastructure tools;
- repository / CI control tools.

A registry entry therefore means only:

> potentially useful capability with reviewed provenance

It does not mean:

> installed, safe to execute, statistically validated, or approved for trading.

## Risk model

MEDIUM is used for read-oriented external research/data tools whose primary
risk is remote dependency, source semantics, credentials or commercial terms.

HIGH is mandatory when the upstream surface can mutate external state or spend
money, including:

- x402 wallet payment;
- Telegram message/account mutations;
- Cloudflare infrastructure mutations;
- GitHub repository mutations;
- GitHub workflow dispatch/cancel/rerun operations.

## Authority

V0.1 authorizes only:

- storing candidate metadata;
- exact upstream commit pins;
- license/risk metadata;
- deterministic validation of the registry itself.

V0.1 does **not** authorize:

- automatic installation;
- MCP runtime execution;
- external network calls;
- secret/API-token/session access;
- x402 or other wallet payments;
- repository mutation;
- GitHub workflow mutation;
- Cloudflare mutation;
- Telegram sending;
- Strategy Router integration;
- Daily Opportunity integration;
- R2 access;
- holdout access;
- training;
- model promotion;
- real-money orders;
- real live trading.

Each candidate must move through a separate evaluation before any adapter,
runtime or production activation can be proposed.
