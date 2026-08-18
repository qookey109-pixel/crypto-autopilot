# Historical Universe V0.1

## Purpose

Historical Universe V0.1 prevents survivorship bias caused by projecting today's active crypto universe backwards into older backtests.

A market is eligible at a historical timestamp only when the repository has explicit evidence that the required provider/market/interval coverage includes that timestamp.

## Core rule

**No evidence, no historical membership.**

The index never extrapolates before `available_from_ms` and never extrapolates after `available_to_ms`.

A market observed in 2026 therefore cannot be assumed to have existed in 2020 unless separate authority covers 2020.

## Record identity

Historical coverage evidence is keyed by:

`provider + market_type + symbol + interval`

Each record also freezes:

- inclusive availability start/end timestamps,
- evidence type,
- source reference,
- optional SHA-256,
- explicit native/proxy provenance.

## Multi-timeframe eligibility

The V0.1 strategy uses native `15M`, `60M`, and `4H` data. The default historical-universe query therefore requires coverage for **all three intervals** at the requested timestamp.

A symbol with only `15M` and `60M` authority is not admitted to the default backtest universe.

## Provenance separation

`native` is explicit and is never inferred from a provider name.

External/proxy observations may be indexed for research, but `native_only=True` excludes them from a native historical snapshot.

This preserves the existing rule that Binance or any other external source cannot silently become Pionex-native authority.

## Partition receipts

`record_from_partition_receipt` accepts verified per-partition historical receipts:

- `PASS` + `audit_ok=true` creates bounded coverage from the receipt's actual first/last timestamps.
- `NO_DATA` creates no membership record.
- failed/unknown statuses or failed audits are rejected.

The caller must explicitly declare whether the receipt represents native or proxy data.

## Conflict gate

Overlapping non-identical authority for the same provider/market/symbol/interval is rejected with `HistoricalUniverseConflictError`.

This is deliberately conservative. Overlap must be reconciled before it can influence a backtest universe.

## Snapshot contract

A snapshot freezes:

- query timestamp,
- provider,
- market type,
- required intervals,
- native-only policy,
- sorted eligible symbols,
- sorted authority references used by the snapshot.

This makes historical universe selection deterministic and auditable.

## Non-goals

V0.1 does not yet:

- discover exchange listing/delisting history automatically,
- claim exact listing dates from the first observed candle,
- splice proxy data into Pionex-native authority,
- rank historical markets by historical liquidity,
- reconstruct the final 8-year / ~250-market universe automatically.

Those require source acquisition and separate evidence.
