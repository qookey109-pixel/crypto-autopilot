# Prospective Shadow Analysis V0.1

Status date: 2026-10-06

Status: **PREPARED RESEARCH ONLY / NO PROMOTION SEMANTICS**

## Role

This module is the aggregation layer after Prospective Shadow Test V0.1.

It consumes frozen signal/outcome pairs and summarizes the evidence required by
the 2026-10-06 integration plan. It does not collect data, call a provider,
schedule a workflow, select a winner, or modify production behavior.

## Review window

The report recommends a prospective observation period of 30 to 90 days.

The analysis reports:

- COLLECTING when the observed timestamp span is under 30 days;
- REVIEW_WINDOW from 30 through 90 days;
- EXTENDED_WINDOW when collection continues beyond 90 days.

These labels describe observation maturity only. REVIEW_WINDOW is not PASS.

## Metrics

For +1h, +4h, +12h and +24h the analyzer reports:

- observed sample count;
- mean raw market return;
- mean MFE;
- mean MAE;
- Qookey directional win rate / average win / average loss / expectancy when a
  MATCH record contains a usable LONG/SHORT direction;
- comparison-signal directional metrics when its direction is available.

Expectancy follows the report definition:

P(win) × AvgWin − P(loss) × AvgLoss

Signal latency is summarized separately for Qookey and the comparison source.
NO_TRADE outcomes are counted as AVOIDED_LOSS, MISSED_GAIN or UNRESOLVED using
the already-frozen 24h shadow outcome.

## Integrity

Both signal and outcome SHA-256 IDs are recomputed before aggregation. Duplicate
signal IDs, mismatched signal/outcome IDs or symbol mismatches fail closed.

## Drawdown limitation

This version intentionally does not calculate a portfolio drawdown from
potentially overlapping shadow signals. Doing so would imply a position sizing
and portfolio construction policy that this research layer does not have.

A later validation layer may calculate drawdown only after a preregistered,
non-overlapping portfolio simulation policy exists.

## Production boundary

Even a positive expectancy in this report cannot change:

- Daily Opportunity Engine V0.1;
- Strategy Router thresholds;
- Risk or Portfolio gates;
- Core100 model status;
- Paper or live execution authority.

A separate cross-asset and out-of-sample review is required first.
