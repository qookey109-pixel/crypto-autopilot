# Cloud Paper operation evidence V0.3

## Problem and prepared behavior

A same-content conditional-create collision can produce an R2 PUT attempt that
does not create an object. Earlier reports computed write attempts from created
objects and set replays to zero, so they could claim `KNOWN` with an
undercount. A cloud-only regression fixture using the budgeted R2 adapter
reproduced 9 reported attempts versus 10 observed S3-compatible PUT calls.

New V0.3 reports set the status to `PARTIAL` and both R2 write-attempt and
write-replay fields to null. The provider-request value remains separately
populated by the existing provider accounting path. These nulls mean *not
available at report construction time*, not zero. They are not final production
usage, cost, or headroom evidence. The budget guard still reserves attempted
operations independently; this report does not replace the guard or ledger.

The successor reader preserves V0.1 embedded-step and V0.2 compact-step reads,
and validates V0.3 digests, result pointers, state, steps and seals. The existing
frozen predecessors and receipts are not modified. Consumers of V0.3 reports
must use the successor reader and seal verifier.

## Remaining work

A separately reviewed post-completion evidence path must measure and retain
actual attempted operations, including retries, conflicts, failed or ambiguous
writes, and the cost of its own evidence operations. It must not rewrite the
immutable report or treat a successful synthetic test as actual Cloudflare
usage. Account-wide cost and headroom, trusted job identity, all-writer
admission, D1 provisioning and runtime/schedule authority remain unproven.
