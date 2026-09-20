# ZEC Strategy V0.3 — Development Selection Policy V0.1

Status: **FROZEN BEFORE REAL DEVELOPMENT EXECUTION**

This policy closes the remaining numeric ambiguity between the already-frozen
64-candidate / four-fold development matrix and selection of exactly one
development champion.

## Frozen eligibility

A candidate is development-eligible only when:

- every chronological development fold contains at least **30 realized trades**;
- the candidate's **worst fold return is strictly greater than 0%**.

The 30-trade rule mirrors the downstream Statistical Edge Gate V0.1 minimum
sample floor as a conservative activity screen. It does not mean 30 trades prove
an edge. Requiring a positive worst fold prevents a zero-trade or losing annual
fold from becoming the winner merely because other candidates performed worse.

## Frozen robust-first order

Eligible candidates are ordered by:

1. highest worst-fold return;
2. highest median-fold return;
3. lower worst-fold drawdown;
4. higher total realized trade count;
5. deterministic candidate id.

No validation or fresh-confirmation result participates in this ordering.

## Frozen local-stability rule

A local neighbor differs by exactly one **adjacent** value on exactly one frozen
candidate axis.

The development leader may be frozen only when at least **two** adjacent
neighbors:

- independently pass the same per-fold trade-count and positive-worst-fold
  eligibility rules; and
- retain at least **75%** of the leader's worst-fold return.

The two-neighbor / 75%-retention values are ex-ante project governance choices.
They are intentionally frozen before real V0.3 development results are viewed
and are not claimed to be scientifically optimal.

If the rule fails, the result is an isolated-peak rejection. The system must not
silently select the second-ranked candidate or change the tolerance after seeing
the matrix.

## Authority

Freezing this policy does **not** authorize execution of the historical
development matrix. The current development contract still has
`offline_development_runner_authorized=false`.

It also authorizes no:

- fresh confirmation read;
- provider network request;
- R2 read/write;
- replacement holdout access;
- source switch;
- model or strategy promotion;
- formal trade plan;
- real-money order;
- live trading.

The next execution step therefore remains a separate explicit authority change.
