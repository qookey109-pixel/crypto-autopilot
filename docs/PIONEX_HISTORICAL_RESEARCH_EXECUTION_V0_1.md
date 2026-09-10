# Pionex Historical Research Execution V0.1

## Outcome

This authority runs exactly one cloud-hosted, Pionex-native public-futures
history pilot: `BTC_USDT_PERP` at `15M`, `60M`, and `4H`. It establishes
provider pagination behaviour, complete-candle availability, Parquet size and
R2 exact-byte publication evidence before any 150-market materialization.

It is deliberately not a declaration that 150 markets, a historical universe,
or a backtest dataset already exists.

## Required order

1. Verify the prepared research-pool config SHA-256 and the execution window.
2. Construct the authorized R2 store and check whole-bucket FREE-ONLY headroom
   before any Pionex request.
3. If the SHA-bound pilot latest pointer already exists, return
   `ALREADY_COMPLETE` without a provider request.
4. Fetch only the configured public K-line endpoint, paginating backwards at
   no more than three requests per second.
5. Reject duplicate, misaligned, invalid or gapped intervals before any write.
6. Build zstd Parquet; reject a run larger than the declared reservation.
7. Recheck whole-bucket headroom, publish immutable interval objects and
   receipts, read every object back by SHA-256, then write the latest pointer
   last.

## Boundary

The workflow is `workflow_dispatch` only: no schedule is added or changed.
It has no private Pionex credential, no account/balance/order method, no
Binance input, no holdout access, no raw-history R2 read path, no training,
no model promotion and no trade or live-trading authority.

The 150-market stage requires a later authority that binds this pilot's actual
row count, interval continuity and measured Parquet bytes. A missing or gapped
provider interval is evidence to review, not permission to interpolate or
substitute another provider.
