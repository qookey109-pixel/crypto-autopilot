# Research Signal Layer V0.1

Status: **PREPARED / RESEARCH ONLY**.

This layer keeps three evidence streams separate:

1. latest closed market candles for Paper Broker candidate generation;
2. append-only historical candles for later walk-forward training;
3. timestamped KOL forecasts for an independent challenger feature.

The implementation in `src/crypto_autopilot/research/signal_layer.py` does not
fetch providers, construct an R2 client or trigger a strategy. It validates
evidence before a future separately authorized ingestion workflow can use it.

## Rolling candle contract

Only a candle whose close time is at or before ingestion time is accepted.
Exact duplicates are idempotent. A conflicting payload for the same
provider/symbol/interval/open-time identity fails closed and requires a new
authority. Pionex, Binance Spot and Binance USD-M records cannot be merged into
one provider stream.

## KOL contract

Each forecast carries a source URL, publication time, ingestion time, target
time, direction, confidence and content SHA-256. Evaluation ignores outcomes
that are not yet observable. The result reports accuracy, Brier score, coverage
and lift versus a simple majority baseline. It is descriptive evidence only;
KOL data cannot directly create a trade plan or promote a model.

## Precision target

The 100% target applies to data integrity, time alignment and no-lookahead
checks. Prediction accuracy cannot be guaranteed at 100%. Candidate feature
groups must beat a chronological naive baseline after fees/slippage and remain
calibrated across multiple walk-forward periods before becoming a challenger.

External KOL ingestion and production R2 writes remain disabled under
`config/research_signal_layer_v0_1.json` until a separate authority names the
approved sources, rate limits, retention and namespace.
