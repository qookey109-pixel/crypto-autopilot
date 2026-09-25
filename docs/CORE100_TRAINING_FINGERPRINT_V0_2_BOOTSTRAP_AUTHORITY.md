# Core100 Fingerprint V0.2 One-Time Bootstrap Authority

Status: **AUTHORIZED_NOT_ACTIVE**. User authorization was given on 2026-09-25 for the exact bounded scope prepared in PR #503. This document and its receipt record that decision; neither allows execution until the authority and matching implementation are merged to `main`.

## Authorized once

After the authority config/receipt and a separately reviewed implementation are both on `main`, one explicit `workflow_dispatch` of the existing Binance USD-M Core100 training workflow may establish the first V0.2 baseline from the already completed dataset:

- 100 markets, 10 shards, 14,274 expected partitions; intervals 15m/1h/4h; source months 2022-08 through 2026-07.
- The bounded R2 reads and writes are enumerated in the versioned authority config. Whole-bucket key/size pagination must prove the 8,000,000,000-byte FREE-ONLY limit before data reads and again before writes.
- Write one immutable model/metrics/manifest run under the dedicated V0.2 run prefix, verify exact existing-object equality and SHA-256 readback, then write the separate V0.2 latest pointer last.
- Preserve the V0.1 latest pointer without reading, reusing, migrating, or overwriting it.

The run must be on `main`, use the exact `bootstrap_v0_2=true` input, have attempt 1, and prove via paginated GitHub Actions run metadata that it is the only run carrying the fixed `CORE100_V02_BOOTSTRAP` run-name marker. The ephemeral token needs `actions:read` only for that metadata check. Duplicate, incomplete, or unreadable run history stops before R2 access.

## After the baseline

The existing weekly workflow may compare read-only. Exact V0.2 identity returns `NO_CHANGE` with no training or R2 writes. Dataset, runtime, or guard changes return `REVIEW_REQUIRED`. The one-time authority grants no later training or writes.

No provider requests, holdout access, source switching, promotion, trade plan, orders, real trading, local runtime/files, schedule change, or paid service are authorized. The budget remains 0 USD/month.

## Required sequence

1. Merge this versioned authority config and receipt.
2. Implement the run guard, isolated runtime fingerprint collection, comparator-only weekly path, one-time V0.2 training path, and focused cloud tests in a separate PR.
3. Merge only after exact-head reviews and all required GitHub checks pass.
4. Re-resolve live `main`, run metadata, current dataset preconditions, and whole-bucket headroom on the hosted runner.
5. Dispatch exactly once. A dispatch attempt consumes the authorization even if it fails; no rerun is allowed.
