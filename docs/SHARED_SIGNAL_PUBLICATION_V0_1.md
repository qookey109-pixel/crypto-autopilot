# Shared research-signal publication V0.1

Status: IMPLEMENTED_DISABLED; cloud CI required. This is a successor publication
component, not a cutover of the existing V0.2 collector or its schedule.

## Concrete integration

The new `research/shared_signal_publish_v0_1.py` connects the existing
`SharedWriterR2Budget` and `BudgetedR2Store` to the existing research-signal
payload / manifest / latest-pointer layout. Disabled calls perform no admission
query, credential lookup, SDK construction or external request.

Enabled trusted calls require the exact research writer identity, fresh complete
account evidence, a prepaid admission query meter and a binding validator.
Admission happens before S3 construction. The caller must supply the exact
merged execution authority; the boolean flag is not that authority.

Publication requires an envelope of 3 Class A attempts, 5 Class B attempts, and
the exact serialized bytes of the three objects (maximum 2,500,000 bytes).
D1 admission/query-controller costs remain separately prepaid by the existing
meter. No bucket LIST is used: fresh account-wide evidence replaces repeated
full-bucket capacity scans. This does not manufacture such evidence.

Both immutable objects use conditional If-None-Match writes and SHA-256 readback.
An already identical immutable object is read back without rewriting it.
The mutable latest pointer is written only after both immutable readbacks pass,
then itself read back. Failure retains the central reservation and reports
REVIEW_REQUIRED with stage, verified-object count and attempted usage; transport
errors and credential values are not included. There is no automatic retry or
refund. A lost response may have written an object; reports retain that ambiguity.

## Remaining cutover requirements

- The legacy workflow and entrypoint still use their existing versioned route.
  The static four-writer inventory correctly remains unverified.
- This publisher receives an already built research payload. It does not admit
  or fetch provider data; provider acquisition must join the same governed
  successor before claiming end-to-end writer integration.
- Exact finite execution authority, all-writer coverage, fresh headroom,
  prepaid D1 controller and protected claims remain production prerequisites.
- The production entrypoint must bind run ID and slot, serialize the writer
  across runs, and prevent a later stale run from replacing a newer pointer.
  This component does not claim global latest-pointer ordering by itself.
- No existing workflow, credentials, schedule, frozen config/receipt or
  Cloudflare resource is changed. Cloud Paper remains NOT_WIRED / NOT_RUN /
  NOT_CONFIGURED; model quality REJECT and all trading restrictions remain.
- Research publication is not formal PAPER evidence or strategy qualification.

## Cloud verification

`tests/test_shared_signal_publish_v0_1.py` uses a mocked S3 transport and
in-memory query results; it verifies admission ordering, exact operation counts,
unknown coverage, rejection, immutable conflicts, conditional write races,
partial writes/readback failure, lost pointer write, and safe diagnostics.
Existing shared-gate tests independently cover duplicate reservations and
concurrent debit limits. These are synthetic engineering tests, not cloud
account access or production all-writer admission evidence.
