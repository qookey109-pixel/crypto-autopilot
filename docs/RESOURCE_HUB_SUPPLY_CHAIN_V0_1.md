# Resource Hub Supply Chain V0.1

Status: `PREPARED_READ_ONLY`

## Purpose

Use `qookey109-pixel/ai-resource-hub` as an upstream tool catalog and let Crypto Autopilot produce a review-only list of potentially useful integrations.

The relationship is intentionally one-way:

```text
AI Resource Hub / data/resources.json
        ↓
exact GitHub commit binding
        ↓
category + domain-signal filter
        ↓
deterministic relevance scoring
        ↓
review-only candidate registry artifact
        ↓
manual human review
```

V0.1 does **not** install, execute, configure, import, call, or authorize any discovered tool.

## Authority and lineage

The GitHub Actions workflow first resolves the exact `main` commit SHA of `qookey109-pixel/ai-resource-hub`, then downloads `data/resources.json` from that exact SHA. The candidate artifact records:

- upstream repository;
- upstream ref;
- exact upstream commit SHA;
- catalog path;
- catalog schema/version metadata when available.

This prevents a candidate report from claiming it came from an unspecified moving `main`.

## Candidate policy

Policy file: `config/resource_hub_supply_chain_v0_1.json`

V0.1 considers these catalog categories:

- `Finance / Crypto`
- `Data / Analytics`
- `Search / Research`
- `OSINT / Intelligence`

A `Finance / Crypto` resource is eligible from category membership alone. Other categories must also match at least one crypto/market-specific domain signal such as trading, investment, market, macro, forecasting, portfolio, OHLCV, candles, or backtesting. This prevents broad resources such as generic GIS or general-purpose research tools from becoming candidates simply because they are tagged Analytics or Research.

Each accepted candidate receives:

- deterministic `relevance_score`;
- matched categories and domain signals;
- an integration type such as `strategy_validation`, `market_intelligence`, `forecasting_research`, `trading_research`, or `data_analysis`;
- a coarse integration-risk label;
- upstream license/open-source/pricing/status metadata;
- `decision = REVIEW_REQUIRED`.

The score is a discovery heuristic only. It is not a security approval, architecture approval, strategy recommendation, model-selection signal, or profitability claim.

## Safety boundary

V0.1 is manual and read-only. The policy fails closed unless all of the following remain unauthorized:

- schedule;
- automatic install;
- automatic execution;
- automatic adapter creation;
- automatic pull request creation;
- provider access;
- R2 access;
- holdout access;
- source switching;
- automatic strategy mutation;
- automatic model promotion;
- formal trade-plan generation;
- real-money orders;
- live trading.

The workflow has only `contents: read` GitHub permission and uploads a secret-free JSON artifact. It does not write back to either repository.

## Cloud usage

After merge, run **Resource Hub Supply Chain V0.1** from GitHub Actions on `main`.

The workflow:

1. checks out Crypto Autopilot;
2. validates the read-only policy;
3. resolves the exact AI Resource Hub `main` commit;
4. downloads the catalog at that exact commit;
5. builds `candidates.json`;
6. re-validates the safety boundary and review gate;
7. uploads the candidate registry as an Actions artifact;
8. removes disposable runner files.

No Mac-local execution, Telegram, MCP, external model, exchange API, R2 credential, or paid runtime is required.

## What comes next

A future version may add a reviewed `integration-registry.json` lifecycle such as:

```text
discovered → candidate → evaluated → approved → active → deprecated
```

That is deliberately out of scope for V0.1. Any adapter execution, automatic PR, recurring schedule, tool installation, provider call, strategy mutation, or trading authority requires a separate reviewed version and explicit authority.
