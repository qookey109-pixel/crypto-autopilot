# Binance Spot R2 Training Governance V0.5

V0.5 supersedes V0.4 execution without changing its frozen evidence. Weekly
training remains Sunday `02:37 UTC` (`10:37 Asia/Taipei`); monthly universe
review remains day 1 at `03:37 UTC` (`11:37 Asia/Taipei`). The monthly workflow
and weekly production workflow have no push trigger. The next weekly cron is
inside the authority window and may create the first training baseline. The
initial monthly V0.5 baseline requires one successful manual `workflow_dispatch`
before `2026-08-27T00:00:00Z`. That activation is not a recurring manual-run
authority: a manual event is rejected before publication when a verified V0.5
monthly review already exists. Scheduled runs remain distinct, and push
execution remains explicitly unauthorized.

## Weekly flow

```text
frozen-window guard
  -> current Binance Spot USDT/USDC catalog
  -> complete-tail and continuity-audited 1D dataset from 2020
  -> exact ordered feature-contract check
  -> deterministic daily-direction model training
  -> chronological partition fingerprints and walk-forward validation
  -> train-prevalence naive baseline comparison
  -> fee/slippage, net-growth, drawdown and concentration checks
  -> bind the exact config bytes to the V0.5 authority receipt
  -> validate catalog / Parquet / receipt / model / metrics / review contracts
     before R2 client construction
  -> compare market/audited coverage with the prior valid V0.5 receipt
  -> fresh whole-bucket 8 GB hard stop
  -> immutable V0.5 R2 objects and latest pointer written last
```

The absolute data gate requires at least 500 markets, at least 90% audited
markets and zero provider errors. The first V0.5 run is compared with the
SHA-256-verified V0.3 online PASS baseline of 748 requested / 723 audited
markets. Later runs use the preceding verified V0.5 receipt. Requested and
audited counts and total historical row count must each retain at least 80% of
the comparison baseline. A
missing V0.5 pointer bootstraps from V0.3; a present but malformed pointer fails
closed and never falls back. A collapse fails before any new object or pointer
is written.

The dataset receipt is bound to the exact catalog bytes and Parquet SHA-256 /
size. The publisher also checks Parquet columns, provider, market type,
interval, row/symbol/audit counts, continuous audited daily timestamps, OHLCV
bounds and per-symbol tail evidence. Model provider,
target, ordered feature contract and all no-trading authorities must match the
config; metrics must match both the raw and canonical model hashes. The weekly
lineage hashes must match the exact training and review configs.

## Model-result semantics

`status=PASS` means the evidence pipeline completed. It is not a model approval.
`model_quality_gate.status` records `PASS`, `REJECT` or `NOT_READY`. Every
configured class with ready folds must improve on the train-prevalence baseline
in every configured fold for log loss and Brier score. The configured-base cost
scenario must have positive net growth, no more than 50% diagnostic drawdown and
no symbol above 10% of selected signals.

The gate is research evidence only. Even `PASS` has zero promotion, formal
backtest, trade-plan, order or live-trading authority. The prior near-100%
drawdown result is retained as `REJECT`, not erased or presented as usable.

## Monthly and pointer safety

The current catalog must pass the same absolute market-count gate. The first
V0.5 monthly run uses only the verified V0.3 count (748) as its collapse
reference; it does not invent a historical classification snapshot. Later runs
must retain at least 80% of the preceding V0.5 monthly snapshot. Previous
pointers are accepted only when schema, provider, safe run id, exact V0.5
namespace/key and SHA-256 all match. Catalog absence remains review evidence,
not a delisting claim. The newly built review is bound to the exact config and
comparison-baseline governance evidence, then its full contract and no-trading
authority are validated before any review object or latest pointer can be
written to R2. The stop window is checked again immediately before each actual
R2 upload, including the latest-pointer upload.

## Stop boundary

Weekly and monthly V0.5 jobs stop before provider or R2 access at
`2026-08-27T00:00:00Z` and do not automatically resume. V0.5 does not touch the
V0.10 production-critical metadata path or the frozen replacement holdout.
The one-time monthly activation must therefore complete before that same stop;
this repository change does not dispatch it.
