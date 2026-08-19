# Pionex ↔ Binance Equivalence V0.1 Direction Forensics

## Purpose

Investigate the already-frozen V0.1 provider-equivalence FAIL without changing or re-grading that result.

Frozen authority:

`research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json`

The V0.1 Gate remains:

- 45 / 45 pairs evaluated
- 18 PASS / 18 REVIEW / 9 FAIL
- all nine FAIL pairs contain `return_direction_agreement_fail`
- source switch unauthorized
- W1 Trade-Kline materialization unauthorized

## Question

V0.1 close-to-close direction agreement uses the exact sign of every adjacent close difference. It intentionally has no deadband. The forensic question is therefore descriptive:

> When Pionex and Binance disagree on return direction, how large are the two venue returns, and are disagreements dominated by one-provider-flat cases or opposite non-zero signs?

This document does not assume the answer.

## Predeclared descriptive bins

Before the forensic evidence run, the following absolute-return bins are fixed for reporting only:

- 0.1 bps
- 0.5 bps
- 1 bps
- 2 bps
- 5 bps
- 10 bps

These are **not** Gate thresholds. They cannot convert FAIL to REVIEW/PASS and cannot authorize a source switch.

The report also records exact disagreement timestamps, both provider returns in bps, mismatch shape, per-pair summaries, and cumulative counts where both absolute returns are below each fixed descriptive boundary.

## Exact evidence replay

The forensic workflow must:

1. reload the frozen M1A Pionex 45-object overlap from R2 with SHA verification;
2. reload the same 360 official Binance Vision daily archives with official checksum verification;
3. preserve the frozen overlap `2026-08-10T08:00:00Z` through `2026-08-17T07:59:59.999Z`;
4. reproduce all 45 V0.1 pair results and the aggregate 18 / 18 / 9 FAIL result before emitting forensic statistics;
5. fail closed if lineage, timestamps, object hashes, pair counts, or frozen authority boundaries differ.

## Mutation boundary

The forensic workflow is read-only with respect to R2.

It must explicitly report:

- `r2_writes_performed=false`
- `r2_deletes_performed=false`
- `provider_splicing_used=false`
- `new_deadband_applied=false`
- `new_threshold_proposed=false`
- `v0_1_thresholds_changed=false`
- `v0_1_scope_changed=false`
- `source_switch_authorized=false`
- `staged_trade_kline_w1_materialization_authorized=false`
- `trade_plan_authorized=false`
- `live_trading_authorized=false`

## Decision discipline after results

The forensic report can support only a diagnosis.

If it shows a concrete measurement-design issue, a separately versioned V0.2 protocol may be proposed. Such a protocol must be justified, versioned, and frozen **before** evaluating its own evidence. V0.1 remains FAIL permanently.

If it shows material directional divergence, provider substitution remains blocked.

No forensic outcome by itself authorizes W1, Historical Universe membership, backtest admission, automatic trade plans, or live trading.
