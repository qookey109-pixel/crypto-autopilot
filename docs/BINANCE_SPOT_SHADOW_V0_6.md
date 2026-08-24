# Binance Spot Shadow Model V0.6

Status: **PREPARED / NOT ACTIVE**.

V0.6 is a local-only research layer built after the first V0.5 weekly run
returned a model-quality `REJECT`. It compares feature groups on an existing
provider-separated Binance Spot `1d` dataset. It never fetches a provider,
constructs an R2 client, reads the replacement holdout, promotes a model or
touches any trading authority.

## Ablation groups

- `baseline`: the existing five daily features;
- `trend`: baseline plus ADX14, +DI14 and -DI14;
- `price_volume`: baseline plus rolling VWAP distance, volume Z-score and
  Donchian position;
- `volatility`: baseline plus ATR percentile, Bollinger bandwidth percentile,
  realized volatility and Parkinson volatility.

Each group uses the same causal warm-up, chronological split and deterministic
logistic trainer. Results include test log loss, Brier score, accuracy, ECE/MCE
calibration and descriptive ATR/ADX/volume regime slices. Small regime slices
are labeled descriptive-only rather than used as a gate.

## Run locally against an already available Parquet file

```bash
PYTHONPATH=src python scripts/run_binance_spot_shadow_ablation.py \
  --dataset /path/to/spot-1d.parquet \
  --end-exclusive-ms 1787788800000 \
  --output /private/tmp/binance-spot-shadow-v0-6.json
```

The output is ephemeral and must not be treated as a persistent artifact. The
config and experiment identity fingerprints make repeated comparisons
comparable without enabling an online workflow. Each output also contains an
immutable experiment-registry entry bound to the dataset, config, trainer and
environment fingerprints; rejected runs remain evidence rather than being
silently discarded.

Funding, mark-index basis and open interest are intentionally excluded from
this Spot shadow model; they belong to a separately governed perpetual-
contract/Pionex research path.
