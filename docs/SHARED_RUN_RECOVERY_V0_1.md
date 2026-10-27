# Shared-admitted Live Paper recovery V0.1

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY.

The new composition reuses recovery V0.2 for compact and legacy steps and makes
one shared reservation before constructing any R2 client. Default disabled.
It repairs only missing immutable result seals after full existing verification.
No provider request, account advancement, tick replay, claim takeover or
state/step/tick rewrite is introduced.

Envelope: provider=0, 8 Class A, 64 Class B and 16384 bytes. Four complete
namespace-kind lists (step/result/claim/tick) consume at most four Class A;
at most four seal creates consume the other four. Each list permits at most
four keys in one terminal page. Any truncation, duplicate or invalid key stops;
there is no next-page request or partial-inventory success. The read ceiling
covers the existing verifier's repeated evidence validation and write readback.
Reads are bounded at262144 bytes, each seal at4096 bytes. No retry or refund.
Operation attempts include failures; a failed/ambiguous write reports the
created-seal count as null rather than0.

Every seal uses conditional IfNoneMatch=* and an exact canonical-body readback.
A conflict, failed readback, expired evidence or malformed chain retains full
admission and returns sanitized REVIEW_REQUIRED, never raw provider exceptions.

This is a bounded initial adapter, not scalable indexed recovery. Once any
namespace kind exceeds four objects it deliberately stops, even for an unrelated
run. A future indexed scope must still prove complete fork/orphan coverage;
caller-selected IDs cannot replace that proof. Namespace consistency across
separate lists also requires the caller's trusted authority binding to prove
exclusive serialized writer ownership. This composition alone cannot prove it.

No active workflow/CLI is switched. Existing registry entries remain unverified.
Production token validity, D1 provision, prepaid metering, account-wide usage
and all-writer coverage remain separate prerequisites. No new production
provider/R2/D1 call or Cloud Paper execution has been performed.
