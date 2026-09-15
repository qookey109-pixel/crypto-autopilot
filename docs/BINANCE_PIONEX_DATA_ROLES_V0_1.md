# Binance / Pionex Data Roles V0.1

Status: FORMAL PROJECT ARCHITECTURE POLICY
Date: 2026-09-15

## Core rule

**Binance = large-scale learning database.**

Binance USD-M historical data is the primary large-scale research and model-learning source because it provides the breadth and depth needed for multi-year, multi-market training and walk-forward diagnostics.

**Pionex = final calibration and real trading environment.**

Pionex-native market data is the execution-domain source. It must be used to validate and calibrate models, signals and execution assumptions against the venue where the system is intended to trade before any future live-trading authority is considered.

This role split is intentional. Binance evidence must not be relabeled as Pionex-native evidence, and Pionex does not need to replace Binance as the large-scale learning database.

## Intended pipeline

1. Binance historical market data -> large-scale model learning and research.
2. Binance walk-forward / cost / robustness diagnostics -> reject weak models before venue validation.
3. Pionex-native historical and current market data -> final calibration and execution-domain validation.
4. Pionex-specific validation -> symbol mapping, candle differences, availability, spread/slippage, funding and execution behavior.
5. Only after separate authority and quality gates -> Pionex order execution.

## Current verified Pionex data state

As of 2026-09-15, the repository has Pionex-native evidence, but it is not yet a complete multi-year production training universe.

Verified completed pilot:

- provider: `pionex_public_futures`
- symbol: `BTC_USDT_PERP`
- intervals: `15M`, `60M`, `4H`
- fixed coverage: 2026-08-01 through 2026-08-27 UTC
- scope: complete fixed 27-day capacity sample only
- successful workflow run: `34513815680`

The broader Pionex market registry contains approximately 150-197 selected/candidate markets depending on the governed scope/version, but selection or observability is not the same as materialized historical K-line coverage.

## Explicit current gaps

The following must remain visible as **not complete**:

- **Pionex 150-197 market complete multi-year historical dataset: NOT AVAILABLE / NOT MATERIALIZED.**
- **Core100 model training directly using Pionex-native data: NOT IMPLEMENTED / NOT PERFORMED.**
- Pionex is therefore not yet a full training source for Core100.
- Existing Binance Core100 evidence remains Binance-native and must not be described as Pionex-native.

These gaps are project work items, not failures of the existing Binance training dataset.

## Design consequence

Future work should prioritize building a bounded, governed **Pionex Validation Dataset** before treating Pionex as a model-training source.

The preferred architecture is:

`Binance learning -> model candidate -> Pionex calibration/validation -> Pionex execution`

A future Pionex dataset may become large enough to support fine-tuning, calibration or venue-specific models, but that is a separate milestone and must not be inferred from the current BTC pilot or candidate registry.

## Safety and authority boundary

This policy records architecture and current state only. It does not authorize:

- Pionex full-universe historical materialization
- new provider requests
- R2 writes
- model retraining
- source switching
- holdout access
- automatic model promotion
- formal trade plans
- real-money orders
- live trading

Existing receipts, configs and execution authorities remain controlling for those actions.
