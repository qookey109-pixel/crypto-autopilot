# VWAP Offline Feature Specification V0.1

Status: offline research prototype only; **not a training, signal, routing, scheduling, provider, R2, holdout, promotion, order, or live-trading authority**.

Evidence basis at preparation: repository main `536095cf779c09a07be45367a5b63e7b7b9df39b` after PR #443 merged. Resolve live main again before any later integration or merge.

## Existing contract stays unchanged

`src/crypto_autopilot/features/advanced.py` already computes a causal **20-bar** rolling VWAP using HLC3 price and volume. Its existing `vwap_distance_fraction`, normalized-feature order, readiness semantics, training inputs, model fingerprints, and Paper behavior are unchanged by this prototype.

Twenty bars are not twenty days. This V0.1 module is a separate research surface and is not imported into the current training/Paper feature pipeline.

## Scope

Prototype module:

`src/crypto_autopilot/features/vwap_research.py`

One build call is restricted to one declared:

- provider;
- instrument;
- volume unit;
- fixed candle interval.

There is no cross-venue aggregation, provider relabeling, network acquisition, persistence, or TradingView runtime dependency.

## Price and time semantics

- Price basis: `HLC3 = (high + low + close) / 3`.
- Weight: the declared source candle volume.
- Source bars must pass the Repository candle audit: valid OHLCV, unique/order-aligned timestamps, and no gaps.
- Day anchor: UTC 00:00 by source bar **open** timestamp.
- Week anchor: Monday UTC 00:00 by source bar open timestamp.
- Month anchor: UTC calendar month by source bar open timestamp.
- A feature snapshot is available only at `bar_time_ms + interval_ms`, after that source bar closes.
- Trailing 7-day and 30-day windows use closed bars with close time in `(T-window, T]`.
- The interval must divide both trailing windows exactly; partial-bar windows fail before computation.

## Outputs

Each anchored/trailing window returns:

- VWAP;
- normalized close distance: `(close - vwap) / vwap`;
- volume-weighted population standard deviation around HLC3 VWAP;
- standard-deviation position: `(close - vwap) / weighted_stddev`;
- contributing bar count;
- explicit `ready` and `reason`.

## Fail-closed / not-ready semantics

Input audit failures raise `VwapResearchDataError`; they are not silently interpolated or repaired.

Trailing windows remain `INSUFFICIENT_HISTORY` until the exact bar count for the full 7-day or 30-day interval-aligned window exists.

A window with total volume zero is `ZERO_VOLUME`. A positive-volume window with zero weighted price variance is `ZERO_VARIANCE`; VWAP and normalized distance remain inspectable but the standard-deviation position is unavailable.

## Required prototype checks

Synthetic tests must cover:

- UTC day/week/month reset behavior;
- closed-bar `available_at`;
- 7-day and 30-day warm-up;
- trailing-window eviction;
- prefix invariance so future bars cannot alter earlier outputs;
- zero-volume and zero-variance semantics;
- gaps and invalid candles failing closed;
- provenance metadata preservation.

## Deferred integration

Do not add these outputs to `AdvancedTechnicalSnapshot.normalized_features`, training matrices, Paper routing, strategy scoring, or production schedules in V0.1.

Any training or ablation use requires a separate versioned experiment contract, approved dataset/provenance scope, chronological evaluation, and explicit model-input fingerprint handling.

Cross-venue volume aggregation, 90/365-day windows, Tokyo Initial Balance, automatic signals/routes, and production scheduling remain deferred.
