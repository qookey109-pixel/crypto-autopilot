# Binance Spot R2 Weekly Training and Review V0.4

V0.4 replaced daily model training with one run per week at Sunday `02:37 UTC`
(`10:37 Asia/Taipei`) and a monthly universe review on day 1 at `03:37 UTC`
(`11:37 Asia/Taipei`). Its provider/R2 execution path is now retired in favor
of V0.5. The V0.4 config, receipt, namespaces and prior R2 objects remain
historical evidence and are not rewritten.

## Historical weekly flow

```text
frozen-window guard
  -> current Binance Spot USDT/USDC catalog
  -> complete provider-separated 1D dataset from 2020
  -> deterministic daily-direction model training
  -> expanding-window walk-forward validation
  -> fee/slippage sensitivity
  -> diagnostic drawdown and model-signal exposure concentration
  -> fresh whole-bucket 8 GB hard stop
  -> immutable R2 dataset/model/review objects
  -> latest.json written last
  -> secret-free GitHub artifact
  -> ephemeral runner cleanup
```

V0.4 pipeline `PASS` meant that diagnostics completed; it was not a model
approval. V0.5 introduced the versioned baseline and quality-gate semantics
without mutating historical V0.4 objects.

## Historical monthly review

The V0.4 monthly run compared active-market snapshots, catalog absences and
heuristic tokenized-stock classification changes. Absence was never proof of
delisting, and current membership never authorized historical membership.

## Retirement boundary

The V0.4 workflow files are manual validation-only retirement checks. They have
no schedule, provider call, R2 credential binding or write path. V0.5 remains
subject to the same `2026-08-27T00:00:00Z` stop and no automatic resume.
