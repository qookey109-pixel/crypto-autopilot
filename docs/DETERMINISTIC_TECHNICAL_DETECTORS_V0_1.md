# Deterministic Technical Detectors V0.1

Status date: 2026-10-06

Status: **PREPARED RESEARCH ONLY / NO PRODUCTION INFLUENCE**

## Purpose

This version formalizes the subjective technical concepts selected in the
2026-10-06 integration report into reproducible, causal research definitions.

It does not claim these concepts have trading edge. It does not modify Daily
Opportunity Engine V0.1, Strategy Router thresholds, Risk, Portfolio or Paper
authority.

## Liquidity sweep / reclaim

For each closed bar after a 20-bar lookback:

- high sweep/reclaim: current high exceeds the prior 20-bar high and the close
  returns to or below that prior high;
- low sweep/reclaim: current low breaches the prior 20-bar low and the close
  returns to or above that prior low;
- a bar satisfying both is treated as ambiguous and emits NONE in V0.1.

This turns the discretionary idea of a liquidity sweep into a reproducible event.

## FVG / imbalance

V0.1 uses a strict three-candle geometry:

- bullish FVG: bar[i].low > bar[i-2].high;
- bearish FVG: bar[i].high < bar[i-2].low.

The detector records the gap zone and becomes available only after bar i
closes. V0.1 does not infer profitability from a gap and does not use a future
fill to create the original event.

## Order block / supply-demand proxy

Because discretionary order blocks are not uniquely defined, V0.1 preregisters
an intentionally narrow proxy:

1. current candle body is at least 60% of its high-low range;
2. bullish displacement closes above the previous 10-bar high, or bearish
   displacement closes below the previous 10-bar low;
3. the immediately preceding candle must be opposite-colored;
4. that preceding candle's low/high becomes the candidate zone.

This is a research proxy, not a statement that all market participants define
order blocks this way.

## Harmonic PRZ

Strict swing pivots use two left and two right confirmation bars. Pivots become
usable only after the right confirmation bars have closed.

The latest five alternating pivots are tested against explicit ratio bands for
Gartley, Bat, Butterfly and Crab patterns. A match creates location evidence
only. It is not an automatic reversal signal.

## MACD divergence

Using the same causally confirmed pivots:

- bullish divergence requires a lower confirmed price low and a higher MACD
  histogram value at the second low;
- bearish divergence requires a higher confirmed price high and a lower MACD
  histogram value at the second high.

No pivot is used before its right-side confirmation bars have closed.

## Sidecar integration

Each detector snapshot can be converted directly to one Technical Confluence
Sidecar row. This preserves the research-only separation introduced by PR #768.

## Authority

No provider access, storage write, holdout access, training, model promotion,
candidate reranking, risk change, paper submission, real-money order or live
trading is authorized by this version.
