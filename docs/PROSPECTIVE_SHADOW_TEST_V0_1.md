# Prospective Shadow Test V0.1

Status date: 2026-10-06

Status: **PREPARED RESEARCH ONLY**

## Goal

Provide the objective comparison layer requested in the 2026-10-06 integration
report without changing production decisions.

The test freezes each signal snapshot first and evaluates outcomes later. This
prevents selecting only successful signals after the fact.

## Signal snapshot

A frozen signal record contains:

- timestamp / symbol;
- reference price;
- Qookey candidate payload;
- Router status: existing ROUTES_READY / NO_TRADE is preserved, with ROUTES_READY normalized to the report's MATCH comparison label;
- Qookey detection timestamp;
- optional external/comparison signal and direction;
- optional event-observed timestamp;
- Qookey and comparison signal latency when the event timestamp is known.

The signal ID is a deterministic SHA-256 over the canonical snapshot.

## Outcome windows

Fixed future windows are:

- +1h
- +4h
- +12h
- +24h

For each exact available horizon the evaluator records:

- terminal raw return;
- MFE from the signal reference price;
- MAE from the signal reference price.

If the exact horizon close is missing, V0.1 emits MISSING_EXACT_HORIZON rather
than interpolating or silently choosing another bar.

## NO_TRADE quality

When Qookey returns NO_TRADE and a comparison direction exists, the 24h
direction-adjusted result is classified as:

- AVOIDED_LOSS when the comparison direction would not have produced a positive
  raw directional return;
- MISSED_GAIN when it would have produced a positive raw directional return.

This label is descriptive. It is not itself an expectancy estimate.

## Evaluation principle

Win rate alone is insufficient. Later aggregate evaluation should combine
return distribution, MFE/MAE, drawdown, signal latency and NO_TRADE quality.
The production system remains unchanged until a separately versioned
cross-asset/out-of-sample validation passes.

## Authority

This module performs research evaluation only. It grants no candidate
reranking, Strategy Router change, Risk/Portfolio change, paper submission or
live-trading authority.
