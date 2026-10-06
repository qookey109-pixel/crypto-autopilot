# Prospective Shadow Collection Execution V0.1

Status date: 2026-10-06

Status: **AUTHORIZED NOT ACTIVE UNTIL IMPLEMENTATION MERGE**

## Authorized purpose

This authority advances the PREPARED_NOT_ACTIVE proposal merged in PR #771 into
a bounded cloud research collection.

The authorized scope is:

- GitHub Actions Artifact research persistence instead of R2/D1;
- a Prospective Shadow Collection V0.1 cloud workflow;
- public no-key Pionex and CoinPaprika evidence only;
- no automatic orders or production-model influence.

The original proposal remains historical evidence and is not rewritten.

## Runtime boundary

The authorized schedule is every four hours at minute 17 UTC.

Each natural run may make at most:

- 8 public Pionex requests;
- 2 public CoinPaprika requests.

There are no provider API keys and no automatic provider retries.

The run may also read at most 100 prior artifacts from this exact prospective
shadow workflow so that causal 4H macro-context observations can warm up and be
assembled without R2 or D1.

## Why four-hour batch settlement replaces hourly settlement

PR #771 proposed hourly outcome settlement. V0.1 execution intentionally uses a
single four-hour batch cadence instead.

Reason: exact +1h/+4h/+12h/+24h outcomes are historical candle facts once their
target close exists, so an hourly job is not required to preserve exact-horizon
semantics. The later four-hour run can evaluate the exact +1h bar without
changing the frozen signal timestamp.

Advantages:

- 6 scheduled runs/day instead of 24;
- lower GitHub Actions usage;
- fewer public-provider requests;
- simpler immutable artifact lineage.

Trade-off:

- outcome labels may appear up to roughly four hours after they become
  observable.

This delay affects reporting latency only. Given the project FREE-ONLY / 0 USD
constraint, the four-hour batch design is preferred.

## Data sources

Pionex public futures:

- common symbols;
- perpetual tickers;
- perpetual book tickers;
- bounded 60M klines for the governed top-five research scan.

CoinPaprika Free:

- /v1/global;
- /v1/tickers/eth-ethereum.

CoinPaprika is used only for normalized current TOTAL3 / BTC-dominance context
through the already-reviewed Context Forward Capture parser.

No raw provider response body is preserved. Only normalized, secret-free
evidence and payload hashes may enter the artifact.

## Warm-up behavior

A ready Market Regime needs 21 aligned 4H context observations.

Until enough valid historical artifacts exist, collection remains active but
Daily Opportunity evaluation fails closed as REGIME_UNAVAILABLE.

The workflow must not invent a neutral regime or relax the existing Daily
Opportunity Engine V0.1 gate.

## Artifact backend

GitHub Actions Artifact is the only authorized durable backend for this
research window.

- retention: 90 days;
- R2: closed;
- D1: closed;
- repository commits as runtime persistence: closed;
- raw provider payloads: closed.

Artifacts are research evidence only. They grant no trading or model authority.

## Comparison-source limitation

The project still has no governed Yaozi private API or exact backend scoring
feed.

Therefore automated Yaozi capture remains closed. Comparison fields may remain
unavailable until a separate governed source is reviewed.

## Trading boundaries

This authority cannot change:

- Daily Opportunity Engine V0.1 scoring or thresholds;
- Strategy Router thresholds;
- Risk or Portfolio Admission;
- Core100 REJECT status;
- model promotion;
- Paper submission;
- real-money orders;
- live trading.

## Delivery order

1. merge this authority and receipt;
2. create a separate implementation PR;
3. require exact-head CI / CodeQL / Dependency-SBOM success;
4. merge implementation to main;
5. allow only the versioned natural 4H schedule and optional manual dispatch.

No runtime collection is authorized from a PR branch.
