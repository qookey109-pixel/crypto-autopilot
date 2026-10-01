# Shared Cloudflare Writer Admission V0.2 (Prepared)

This successor adds a bounded retained-reservation count. A single-row capacity counter is incremented by a database trigger in the same transaction as each inserted reservation. Admission fails closed when the shared database policy cap is reached. Exact idempotent replay does not increment the counter; rejected inserts do not increment it.

The cap bounds ledger row growth; it does **not** provide indefinite operation. This version has no pruning or compaction. Before the cap can be reached, a separate versioned authority must define how old reservations can be safely archived or removed without permitting stale replay, losing rolling-window accounting, or exceeding D1 row/write budgets. Until then the cap is a hard operational stop.

The D1 row-write envelope must include at least two rows for each successful reservation: the reservation row and the capacity-counter update. The shared database policy row starts with a NULL cap, which blocks admission. An approved cap must be installed through a separately reviewed, versioned migration; individual writers cannot choose their own value. No production capacity or resource limits are approved here.

Status: synthetic validation only. D1 remains unprovisioned; Cloudflare requests and production activation remain unauthorized. External account writers are still unconfirmed. This version does not prove D1 concurrency or Cloudflare account-wide coverage.
