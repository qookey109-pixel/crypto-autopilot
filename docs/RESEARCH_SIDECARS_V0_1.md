# Market Event Radar + Technical Confluence + Bounded Decision Sidecars V0.1

Status date: 2026-10-06

Status: **PREPARED RESEARCH ONLY / NO RUNTIME AUTHORITY**

## Objective

This batch implements the first research-only step from the 2026-10-06 external-reference integration review:

> make Qookey more sensitive at the front of the pipeline while preserving the existing conservative execution gates.

It does **not** rewrite Daily Opportunity Engine V0.1. The frozen V0.1 score and threshold semantics remain unchanged.

## Components

### Market Event Radar V0.1

Consumes already-available deterministic measurements for:

- relative volume / volume Z-score
- open-interest change and acceleration
- funding
- liquidation imbalance
- VWAP Z-score
- volatility compression/expansion
- market breadth

It returns point-in-time descriptive event tags only. It performs no network capture and does not rank candidates.

### Technical Confluence Sidecar V0.1

Aggregates caller-supplied deterministic, causal feature labels across 1D / 4H / 1H / 15M / 5M:

- market structure
- liquidity sweep/reclaim
- FVG / imbalance
- order-block / supply-demand evidence
- harmonic PRZ evidence
- MACD divergence

V0.1 only counts bullish/bearish evidence and emits a descriptive confluence label. It does not assert that SMC, harmonic or divergence concepts are profitable.

The exact detector algorithms for FVG, order block, harmonic ratios and divergence remain separate research work and must be preregistered and tested before any production influence.

### Bounded Decision Classification V0.1

Validates offline model output against six closed categorical axes:

- market regime
- direction
- flow state
- event importance
- risk regime
- strategy hint

All probability vectors must contain the complete allowed label set and sum to one. These values are **classification probabilities**, not calibrated trading probabilities.

No Clef / Clef-flash / LLM provider call is made or authorized by this module.

### Opportunity Research Adapter V0.1

Attaches the three sidecars to an existing Opportunity V0.1 payload as extra research evidence.

Hard invariants:

- Opportunity V0.1 score unchanged
- Opportunity V0.1 thresholds unchanged
- Strategy Router thresholds unchanged
- no candidate reranking
- no Risk / Portfolio / Paper authority change

## Intended flow

```text
prefetched / already-computed market evidence
        |
        +--> Market Event Radar V0.1
        |
OHLCV-derived deterministic research features
        |
        +--> Technical Confluence Sidecar V0.1
        |
offline bounded classifier output
        |
        +--> Bounded Decision Classification V0.1
                    |
Daily Opportunity Engine V0.1 (unchanged)
                    |
                    +--> Opportunity Research Adapter V0.1
                              |
                              +--> research evidence only
```

## What remains next

1. Implement preregistered deterministic detector definitions for liquidity sweep/reclaim, FVG, order block, harmonic PRZ and MACD divergence using causal candles.
2. Add prospective shadow-report records with timestamp/symbol, +1h/+4h/+12h/+24h returns, MFE/MAE, latency and NO_TRADE quality.
3. Run cross-asset and out-of-sample validation before considering any V0.2 candidate-ranking or Router influence.
4. Only after separate validation and authority may a real decision-model provider be evaluated.

## Authority

This batch grants no provider access, network capture, R2/D1 write, holdout access, training, model promotion, paper submission, real-money order or live trading.
