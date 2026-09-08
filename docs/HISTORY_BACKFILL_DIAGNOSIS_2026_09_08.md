# Historical backfill failure diagnosis — 2026-09-08

Status: DIAGNOSTICS_PREPARED_NOT_DATA_COMPLETION

## Observed evidence

- Formal main inspected: `bd030bc26ee143899511203ee101f007f966d933`.
- Scheduled history run: https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34163690083
- Job: 101870448915. At 2026-09-07T21:37:43Z, the stack reached
  `fetch_partition` -> `ingest_kline_archive` -> `Binance Vision kline audit failed`.
- The checksum, CSV parsing and strictly increasing/unique timestamp checks precede
  this audit gate. The historical log did not name the rejected partition or
  distinguish gaps, misalignment and invalid OHLCV. The exact data defect remains
  unverified; it must not be guessed from the generic exception.
- In `materialize_shard`, all partition fetches must finish before the shard write
  loop. This exception stops that invocation before its shard publication and
  completion-state update; it does not establish whole-bucket state or absence of
  writes from earlier invocations.

## Bounded change

Add archive identity, verified SHA-256, row count and aggregate audit-failure
counts to the existing exception. No raw candles, timestamps, credentials,
environment values or provider response bodies are included.
Preserve every rejection condition, checksum requirement and provider label.
Synthetic regressions cover gaps, misalignment, negative volume and checksum
precedence. No cloud schedule, authority config, frozen receipt or R2 object changes.

## Completion gates

1. Merge the reviewed diagnostics after CI passes.
2. Inspect the next existing scheduled history run for the exact partition and
   aggregate audit reason. Do not manually replay the frozen metadata window.
3. If source data is invalid, preserve rejection. Source revision, replacement,
   exclusion, interpolation or selection changes require an explicit versioned
   decision; do not silently force 100-market completion.
4. Only a verified complete governed dataset may enter its existing research
   trainer. A successful job can be a dependency-waiting result, not training PASS.
5. Pionex Paper V0.2 remains PREPARED_WAITING_FOR_HOLDOUT_AUTHORITY. Historical
   Binance completion cannot grant Pionex-native provenance, holdout access,
   automatic model promotion or live execution.

This document is an engineering observation and acceptance checklist, not
new execution authority. No historical data has been repaired by this change.
