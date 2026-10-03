# Shared Cloudflare Writer Budget Gate V0.4 — prepared

## Why this successor exists

The V0.3 lifecycle schema provides writer identities, retention watermarks, and a retained-row capacity gate. Its helper module validates slot/replay and compaction parameters, but it does not provide the account-wide atomic reservation statement that applies daily and rolling resource caps. V0.2's insert helper targets a different V0.2 table and accepts limits from its caller. Neither is the V0.3 production budget gate needed for multiple projects.

V0.4 adds that missing deterministic reservation statement against the V0.3 lifecycle tables. One central V0.4 policy row holds every daily and rolling cap. A writer cannot raise or substitute the caps through function arguments. All NULL policy fields block admission.

## Behavior

- The SQL aggregates reservations across the shared V0.3 table, regardless of writer ID.
- It checks all daily dimensions: provider requests, R2 Class A/B, new R2 bytes, D1 queries, rows read, rows written, and storage growth.
- It checks R2 Class A/B and new bytes over the inclusive rolling 31-day window.
- It checks daily reservation count, registered active writer identity, and retired-slot watermark before insertion.
- The V0.3 database triggers remain a second gate for active writer, capacity, and retirement rules.
- The reservation carries a conservative workload/ledger query/write/storage envelope. The helper rejects fewer than two D1 query attempts, one row read, or the V0.3 schema's seven-row write floor. These are minimum envelope checks, not Cloudflare D1 upper-bound calibration.
- Every reservation and replay-read statement requires a successful prepaid attempt debit before SQL execution. Missing, unavailable, invalid or exhausted metering blocks before that statement.
- Exact replay returns the original reservation. Changed content blocks. Callers must not perform provider or storage access after EXISTING_RESERVATION.
- No reservations are released. Compaction remains a separate operation requiring its own authority.

## Query-attempt accounting

A successful-reservation sum is insufficient: an insert can be rejected without creating a row, and the same retained slot can be read repeatedly. Both consume D1 resources. V0.4 therefore requires an independent `AdmissionQueryMeter` at every SQL call. The meter must atomically debit calibrated statement costs from a durable pool already prepaid against account-wide D1 headroom and return `CHARGED`. A missing or failed debit stops before D1 access.

The same pool must cover all writers and survive helper calls, process restarts and retries. Each failed transport attempt retains its debit; the helper makes one transport attempt and never refunds or retries it. The controller uses its own live UTC clock, so replaying yesterday's slot charges today's attempt pool. It must not use the protected D1 query to obtain permission to fund that query recursively. Its own control operations need a separately proven, finite prepaid envelope.

The controller is **not implemented or wired to production** in this version. CI uses an in-memory synthetic pool solely to verify ordering, cross-writer use, repeated-replay exhaustion, rejected-query charging and no refund after failure. That fixture does not prove durable or concurrent account metering. A no-op callback is not an approved controller.

Capacity review must cover the sum of all workload reservations, prepaid admission/replay pools, controller overhead and other unreflected account usage. The workload envelope retains its ledger floor; conservative overlap may overreserve but may not be netted or refunded to hide attempt usage. Central policy ceilings must leave room for the prepaid control-plane allocation. Query rows-read/write/storage estimates still require exact D1 calibration, including aggregate scans and triggers.

Before any activation, the controller adapter must authenticate writer/run authority, enforce a finite allocation and fresh-slot rules, demonstrate atomic durable debits and restart behavior, and prove that every transport query follows this interface. Adding a service requires registration and allocation before its first cloud write; unknown external writers keep account coverage unconfirmed.

## Status and limits

This is a prepared contract and SQLite synthetic validation only. The policy row is created with NULL caps, so it cannot admit any writer until a separate authority sets finite values. No D1 migration, Cloudflare request, writer integration, provider call, R2 access, or workflow schedule is included in this PR.

SQLite does not prove Cloudflare D1 transaction, concurrency, foreign-key, trigger, or meta.rows_read/meta.rows_written behavior. V0.3's D1 metadata calibration requirement remains open; do not infer production safety from CI. External repository/service writers remain unknown and must be owner-attested and registered before any account-wide claim.

## Production prerequisites

Before production use, require a complete owner-attested inventory of current and planned writers, registration and shared-ledger integration for every writer, a separately authorized D1 provisioning and policy update, fresh account-wide R2/D1 usage and headroom evidence, zero-cost fixed/usage review, finite caps below actual free-tier limits, exact D1 cost/concurrency calibration, a verified durable prepaid attempt controller with bounded self-costs and restart behavior, and separate authority for compaction. Cloud Paper remains disabled until the full product's data, strategy, recovery, and controlled PAPER gates pass.

CLOUD_ONLY / FREE-ONLY / 0 USD / PAPER-LIVE-PAPER ONLY. Holdout, source switch, promotion, real-money orders, and live trading remain closed.
