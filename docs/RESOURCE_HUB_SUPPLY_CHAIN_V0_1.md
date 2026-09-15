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

A `Finance / Crypto` resource is eligible from category membership alone.

Starting with policy `v0.1.1`, non-Finance resources must match at least one **strong** finance/market signal. Broad terms such as `market` and `portfolio` are retained as weak scoring signals, but they cannot make a non-Finance resource eligible on their own. Strong evidence includes terms such as trading, crypto, investment, backtest, risk, macro, forecasting, geopolitics, market data, portfolio management, asset allocation, price data, exchange, OHLCV, or candles.

This hardening came from the first production proof: general AI/automation and design resources were incorrectly admitted when their catalog text happened to contain only `market` or `portfolio`. The permanent regression suite now requires those false positives to stay excluded while still allowing a genuine market-data/OHLCV resource through.

Each accepted candidate receives:

- deterministic `relevance_score`;
- matched categories and domain signals;
- explicit `strong_matched_signals` evidence;
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

## First production proof

The first manual production run on 2026-09-15 scanned AI Resource Hub commit `7b19de82cd53d851fa5dd478bc1801d383f6c920` and demonstrated that the end-to-end lineage/artifact path worked. It also exposed two false positives caused by weak terms (`market` and `portfolio`), which motivated policy `v0.1.1` and its permanent regressions.

## First candidate evaluation

The first reviewed candidate is `anti-gambling-trader-tw` (反詐投資王), bound to upstream commit `9d938b64c80ee29363aed496ba4e61d9110a7222`.

Evaluation receipt:

`research/receipts/2026-09-15-resource-hub-anti-gambling-trader-evaluation-v0-1.json`

The result is deliberately **not** an integration approval:

- performance-metric and significance-testing semantics are useful research/cross-check candidates;
- its significance layer is limited by an IID-trade assumption and no block bootstrap;
- its temporal validation is a single chronological holdout, not a replacement for Crypto Autopilot frozen-holdout governance or multi-stage validation;
- its PaperBroker is rejected for crypto-perpetual simulation authority because the short model omits funding, margin lock, maintenance margin, forced liquidation and related costs;
- broker/live scaffold surfaces remain rejected for V0.1.

The next allowed step is therefore an isolated statistical-equivalence/cross-check harness using synthetic and existing non-holdout fixtures. It does not authorize code import, runtime dependency, provider/R2/holdout access, strategy mutation, model promotion, broker connection or order execution.

## What comes next

A future reviewed version may add an `integration-registry.json` lifecycle such as:

```text
discovered → candidate → evaluated → approved → active → deprecated
```

The evaluation receipt above only records a reviewed decision; it does not create an approved/active registry entry. Any adapter execution, automatic PR, recurring schedule, tool installation, provider call, strategy mutation, or trading authority requires a separate reviewed version and explicit authority.
