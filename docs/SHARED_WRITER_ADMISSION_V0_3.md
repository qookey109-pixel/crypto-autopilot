# Shared Cloudflare Writer Admission V0.3 — bounded lifecycle (prepared)

## Status and scope

This is a **prepared, synthetic-validation-only successor** to Shared Writer Admission V0.2. It does not provision D1, execute Cloudflare requests, migrate a V0.2 database, authorize compaction, or connect any production writer.

The user confirmed that other projects/services may later use the same Cloudflare account. The external writer inventory is incomplete, so no account-wide usage, storage headroom, or zero-cost conclusion is proven. The successor keeps account-wide admission closed until every current and planned writer is owner-attested and registered.

The design retains V0.2's account-wide model: admission reservations aggregate across all writers; writer ID scopes slot idempotency; UTC-day and inclusive rolling-31-day budgets are checked across the shared ledger. A writer contributes one complete resource envelope per canonical time slot.

## Why V0.2 needs a successor

V0.2 has a NULL-by-default retained-row cap and fails closed when it is reached. It never prunes rows, so it cannot support indefinite service. This successor adds bounded retention while protecting each writer from replaying a compacted slot.

The new migration is a **fresh versioned schema**. V0.2 databases and receipts are not changed; no production database exists to migrate.

## V0.3 identity and stale-replay rules

- A slot identity is canonical `slot:<slot_at_ms>`; `idempotency_key` must equal the slot ID. The unique key is `(writer_id, slot_id)`, so two registered writers can reserve the same slot while one writer cannot create two envelopes for that slot.
- The envelope carries both scheduled slot time and actual reservation time. Callers must provide a bounded freshness window and runtime time before any external access.
- The caller reads the retained reservation by `(writer_id, slot_id)` before freshness rejection. `classify_reservation_replay` returns `RETURN_EXISTING` only when every immutable envelope field matches; changed or malformed content blocks as an idempotency conflict. This path must not repeat provider or write access. If the row has been compacted, the missing row goes through freshness and watermark checks and stale replay blocks.
- Compaction deletes only rows with `reserved_at_ms < now_ms - 31 days`. The 31-day boundary remains included in rolling totals.
- The delete trigger monotonically advances a per-writer maximum purged slot watermark and decrements the active retained-row counter. Any attempt to reinsert a slot at or below that watermark fails closed. Writer identities and watermarks are never deleted.
- Both lifetime writer identity capacity and active reservation capacity start NULL and block writes. Values must be finite, shared-policy values, not writer-selected values. Reaching any cap blocks further admission until separately reviewed policy changes.

The helper validates canonical and fresh slot IDs before any provider or persistence operation. The SQL trigger is a second defense after compaction.

## Bounded maintenance and its cost

Compaction is an explicit, bounded SQL delete. The caller must provide a finite maximum batch size and a separate versioned compaction execution authority. Neither has an approved production value here. The SQL runs one delete statement, with capacity and watermark changes performed by triggers; production atomicity must still be checked against Cloudflare D1 under a future separately authorized validation.

The Python helper computes a schema-derived **minimum** D1 rows-written envelope:

- One new reservation: at least 7 written rows, including reservation table/index entries plus the capacity counter and its key.
- A compaction reservation plus a batch of N deleted reservations: at least `7 + 8N` written rows, including deleted reservation table/index entries, the capacity counter and the per-writer watermark update.

These are lower bounds from this synthetic schema, not production upper bounds. Before a production operation, its finite envelope must reserve the ledger's own reservation and query costs, all indexes and triggers, target operation costs, and storage growth. Missing/old usage data, a missing envelope, or post-query `rows_read`, `rows_written`, or `size_after` outside the bound must block and preserve evidence. The meter reservation itself must be included before execution; do not rebate or release ambiguous reservations.

The D1 Free tier is not just a 5 GB account storage ceiling: Cloudflare currently documents 500 MB per database, 5 GB total account storage, 5 million rows read/day, and 100,000 rows written/day. Since September 1, 2026, exceeding a daily row limit causes D1 queries to fail until the UTC reset. These published limits do not show this account's plan, usage, other databases, or headroom. Revalidate official limits and account evidence before any production activation.

## Validation

GitHub CI uses SQLite fixtures to exercise:

- multiple writers reserving one slot and cross-writer daily/rolling aggregates;
- exact retained replay returns the existing envelope, changed replay conflicts, and missing stale replay blocks;
- execution of the same bounded compaction SQL constant used by the prepared helper;
- NULL/default capacity blocking and capacity release on compaction;
- finite bounded compaction, the inclusive 31-day boundary, and watermark advancement;
- replay of a compacted stale slot being rejected;
- exact idempotency constraints, freshness, and future-slot rejection;
- explicit-authority and minimum write-envelope checks.

SQLite confirms the deterministic schema and helper behavior only. It does not establish D1 metering, transaction semantics, trigger behavior, production concurrency, account-wide usage, or storage size. No D1 access/provisioning, migration, external writer integration, workflow schedule, or runtime activation is part of this change.

## Production gates

Before any use outside GitHub CI, all conditions remain required:

1. Owner-attested inventory of every current and planned account writer, plus registry and admission integration for each.
2. Fresh account-wide D1/R2 usage and storage evidence, with plan, fixed charges, and complete zero-dollar scope established.
3. Finite policy caps below current per-database and account-wide limits, supported by actual storage-size and usage headroom.
4. Exact Cloudflare D1 metadata calibration for the reservation, replay read, aggregate query, and compaction statement, including trigger and index costs.
5. Separate versioned authority for D1 provisioning/migration and another explicit authority for production compaction execution.
6. Every existing writer and any new writer uses the same account-wide ledger before external access.
7. Controlled PAPER acceptance after market-data and strategy gates pass.

Until then, `activation_enabled=false`, D1 stays unprovisioned, Cloud Paper remains disabled, and unknown usage fails closed.

## Official Cloudflare references

- [D1 pricing and row accounting](https://developers.cloudflare.com/d1/platform/pricing/)
- [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)
- [D1 Free daily limit enforcement (2026-09-01)](https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/)
- [D1 batch and transaction behavior](https://developers.cloudflare.com/d1/worker-api/d1-database/)
- [D1 query metadata](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)

CLOUD_ONLY / FREE-ONLY / 0 USD / PAPER-LIVE-PAPER ONLY. Holdout, source switching, promotion, real-money orders, and live trading remain closed.
