# Prepaid D1 Runtime Gateway V0.1

## Scope

Implementation is disabled by default. `cloud_runtime_v0_2.build_runtime_composition`
connects the claimed GitHub query meter, the V0.4 shared-writer gate and the
existing Cloud Paper slot/account/persistence composition. Construction sends
no request. Production remains NOT_WIRED / NOT_RUN / NOT_CONFIGURED.

The successor does not replace the validated account or paper engine, change
strategy eligibility, provision D1, create claim tags/protection, enable cron,
or consume Billing History V0.2. Historical contracts and receipts remain intact.

## Before every D1 request

- Require a concrete factory-claimed PrepaidQueryMeter, bound to writer and
  canonical current slot, and independently fresh account-wide D1 evidence.
- Only six exact SQL constants are accepted: shared admission/read, legacy
  slot admission/settlement/read and verified recovery receipt. Arbitrary SQL,
  cross-writer/cross-slot parameters and the old recursive D1 shared-row
  reservation statement are rejected before HTTP.
- Debit the ticket before exactly one HTTP request. There is no retry/redirect
  or raw response logging. Timeout at most 10 seconds; response at most 256000
  bytes. Per-attempt local guard and original evidence are rechecked.
- Require integer, nonnegative rows_read, rows_written and size_after in the
  returned D1 statement metadata. Compare actual rows and database growth with
  the calibrated ceilings. Missing/invalid metadata, excess or lost response
  yields D1_LEDGER_REVIEW_REQUIRED and poisons the client. No refund or retry.
- size_after is total database bytes after commit, not growth. Compare against
  independently measured, fresh evidence bound to the target database. Keep
  the greatest confirmed size; never manufacture a fresh measurement. Concurrent
  external growth can conservatively block this adapter.

Calibrate RESERVATION for the worst of all four write SQL statements and
REPLAY_READ for both reads, including triggers/index maintenance and rejected
attempts. The local guard must cover each calibrated class ceiling. SQLite
fixtures exercise actual SQL; they do not measure production D1 billing.

Official response semantics:
[D1 query API](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)
and [D1 pricing and rows](https://developers.cloudflare.com/d1/platform/pricing/).
Optional API fields are mandatory evidence for this product's fail-closed gate.

## Workload admission and recovery

Before any provider or R2 operation, atomically reserve the full shared writer
workload, then reserve the existing Cloud Paper slot. The central reservation
is never released, even after legacy detail settlement. A duplicate shared
slot stops before R2/provider access.

V0.4 admission and the new transport both debit the same prepaid ticket:
**two conservative debits but one HTTP request per admission statement**.
Legacy queries consume one debit each. A successful NO_TRADE slot requires
three actual D1 requests and four ticket debits. Rejected admission/replay
requires at most two actual requests/four debits. All finite tickets are
prepaid in full; accounting never subtracts a rebate.

Reconstruction for a later current slot uses a new durable ticket and fresh
workload admission, then verifies and continues the existing R2 account.
Historical settlement recovery is blocked unless a separately reviewed current
R2 workload envelope exists. An old reservation cannot fund new-day recovery
reads. Existing readers/formats stay available unchanged for their authorities.

## Authority and future writers

Claim factories accept a strictly bounded successor authority file path on
exact live main; the frozen disabled prepared controller config is not edited
to activate execution. The default stays disabled.

The owner expects additional projects/services later. This is a requirement
for extensibility, **not confirmation that the current account inventory is
complete**. Register and allocate each writer before its first cloud write.
Unknown/unregistered writers receive no default capacity. An external service
which bypasses this gateway cannot be constrained by this repository: account
coverage must detect/reserve its usage or stop. Do not allocate all account
headroom to Crypto Autopilot, create overlapping epochs, or treat unknown
headroom as sufficient.

Next production gates: current account inventory/cost/headroom, an independent
fresh evidence producer, finite immutable execution scope and calibrated costs,
protected GitHub claims, D1 provisioning/migration authority, controlled main
PAPER acceptance, then natural schedule and Dashboard evidence.

## Engineering checks

GitHub-hosted CI exercises: disabled before credentials, missing/stale/mismatched
evidence, exact SQL/identity binding, prepaid send boundary, missing/bad/overlimit
metadata, ambiguous write/poisoned client, finite pool exhaustion, authority path
validation, actual SQLite shared+legacy admission, full empty-registry NO_TRADE
persistence, next-slot account continuation, duplicate rejection and old-slot
recovery refusal. Only mocks/synthetic SQLite/S3 are used: zero production calls.

FREE-ONLY / 0 USD / PAPER-LIVE-PAPER ONLY / CLOUD_ONLY.
