# Binance Spot R2 Automated Training V0.3

V0.3 makes Cloudflare R2 the canonical online store for the Binance Spot
internal-training dataset and the output of scheduled research model training.
Local files remain rebuildable caches and test inputs, not the online source of
truth.

## Daily flow

```text
GitHub Actions daily schedule / manual dispatch
  -> frozen-window guard (before provider or R2 access)
  -> Binance public Spot catalog (USDT + USDC)
  -> complete 1D history build and audit
  -> deterministic time-split research model training
  -> fresh whole-bucket R2 inventory / 8 GB hard stop
  -> immutable dataset snapshot + catalog + receipt upload
  -> immutable model + metrics + manifest upload
  -> latest.json pointer written last
```

The workflow is `.github/workflows/binance-spot-r2-automated-training-v0-3.yml`
and runs at `02:37 UTC` daily. It also supports `workflow_dispatch`.
Changes to the V0.3 workflow, configuration, or its exact dataset/training code
paths on `main` also trigger one run, which makes first deployment and subsequent
pipeline updates self-verifying without retraining for unrelated site changes.

## R2 layout

```text
market-data/binance_spot/internal-training/v0.3/runs/
  run=<github-run-id>/
    binance-spot-1d.parquet
    market-catalog.json
    dataset-receipt.json

training/binance_spot/daily-direction/v0.3/
  runs/run=<github-run-id>/
    model.json
    metrics.json
    manifest.json
  latest.json
```

Dataset and training-run objects are immutable. The latest pointer is written
last, so a partial upload cannot replace or invalidate the preceding advertised
run. Every uploaded object is read back and verified by SHA-256.

## Baseline model

The first model is deterministic logistic regression, trained separately for:

- crypto;
- stablecoin;
- tokenized-stock candidates;
- other assets.

It predicts whether the next complete daily close is higher using only causal
features already known at the current daily close: 1/3/7-day returns, close vs
7-day moving average, and quote volume vs 7-day moving average. The split is
time-ordered, normalization is fit on the training side only, and rows with
`audit_ok=false` do not enter training.

The model is a pipeline proof and research baseline. Accuracy, log loss, and
Brier score are diagnostics, not a profitability claim or strategy promotion.

## Secrets and safety

R2 credentials are read only from GitHub Actions secrets:

- `CLOUDFLARE_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

No secret value is written to artifacts, manifests, logs, Pages, or the
Repository. The workflow preserves provider provenance and does not authorize
Pionex relabeling, provider switching, Historical Universe membership,
backtest admission, trade plans, real-money orders, or live trading.

The existing replacement-holdout boundary remains binding. At
`2026-08-27T00:00:00Z`, the workflow stops before provider requests and R2
construction. Automatic resume is disabled until a separate post-window
authority exists.
