# Binance Spot R2 Weekly Training and Review V0.4

V0.4 replaces daily model training with one run per week at Sunday `02:37 UTC`
(`10:37 Asia/Taipei`). A monthly universe review runs on day 1 at `03:37 UTC`
(`11:37 Asia/Taipei`). Push-scoped first-deployment runs verify both pipelines
when their exact implementation or authority files change.

## Weekly flow

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

The walk-forward folds use only earlier samples for fitting and later,
non-overlapping samples for validation. Cost scenarios are zero-cost reference,
the configured 5 bps taker fee plus 2 bps slippage per fill, and a 10/5 bps
stress case. Drawdown and exposure values are out-of-fold model-signal proxies,
not executed portfolio results or profitability claims.

## Monthly universe review

The monthly run compares the current active catalog with the preceding monthly
snapshot and records additions, absences, asset-class changes and heuristic
tokenized-stock candidate changes. Absence from a current active catalog is not
proof of delisting. A current-membership snapshot cannot reconstruct historical
membership, so survivorship bias remains `REVIEW_REQUIRED` and Historical
Universe membership remains unauthorized.

## Storage and safety

Cloudflare R2 is the only persistent generated-data store. Weekly and monthly
objects use V0.4 namespaces and exact SHA-256 round-trip verification. GitHub
Actions keeps only secret-free evidence and deletes its disposable workspace.
Raw history is not projected to GitHub Pages.

Both workflows stop before provider or R2 access at
`2026-08-27T00:00:00Z`. They do not automatically resume. Formal strategy
backtest admission, automatic model promotion, source switching, replacement
holdout access, trade plans, real-money orders and live trading remain false.
