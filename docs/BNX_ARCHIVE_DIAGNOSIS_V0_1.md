# BNX Archive Diagnosis V0.1

Status: AUTHORIZED_ONLY_AFTER_PROTECTED_MAIN_REVIEW_AND_MERGE

## Purpose and exact scope

Diagnose whether the observed BNXUSDT August 2022 15m monthly archive's 288
missing candles exist in official Binance Vision daily archives.
The original monthly ZIP SHA-256 is
`a3351bdf83dad7f503fb5732c88c85253101954c47b0cdb6791a11d61b131543`.
This investigation is separate from the existing Crypto Core materialization
authority; its output cannot replace a production partition.

The config is `config/bnx_archive_diagnosis_v0_1.json`, SHA-256
`293187ce50a08a73efc233163b3b5d1aa8c5ed48ceaea942e12b39e644dcac63`, bound by
`research/receipts/2026-09-08-bnx-archive-diagnosis-v0-1-authority.json`.

## Execution

Only an explicitly requested fresh manual main dispatch of the existing
`binance-usdm-detailed-history-v0-1.yml`, mode `diagnose-bnx`, may run after
this authority is merged. Run attempts greater than one fail before network
access; another investigation requires another explicit operator dispatch.
No cron or second scheduler is added. The existing workflow concurrency group
serializes diagnostics with backfill.

The dedicated GitHub-hosted diagnostic job has no R2 secret bindings and does
not install dependencies or construct an R2 client. It permits at most 12
public requests, no automatic retries, no redirects or proxy fallback, 30s
per request, 8 MB per response and 20 MB total. ZIP expanded payload is capped
at 8 MB. Deadline is exclusive 2026-10-01T00:00:00Z, checked before every request.
Only the pinned monthly file plus checksums, derived missing days and one
overlapping complete day may be requested; at most five daily archives.
All data is processed in runner memory. Original R2/headroom requirements
continue to apply to the separate materialization path.

## Evidence and repair conditions

- Verify checksum and incident monthly SHA before daily reads. Changed SHA
  reports SOURCE_REVISION_REVIEW_REQUIRED and stops.
- Verify the exact observed 2688-row / one-gap / 288-missing-bar incident,
  sorted unique aligned valid candles and exact August boundary.
- Each daily archive must have the same symbol, interval and provider, a valid
  checksum and complete UTC-day coverage. No partial daily archive is accepted.
- Preserve every monthly OHLCV value. Overlap must agree exactly, and all
  missing timestamps must be supplied by daily rows. No interpolation.
- Audit the complete 2976-row month using the original candle checks.
- Missing file, overlap conflict or incomplete supply cannot yield a candidate.

A successful result is REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY.
Only aggregate counts, archive/date identities and SHA fingerprints are
retained in a 30-day GitHub artifact. No raw rows, repaired CSV or candles are
published. Failure logs use bounded status codes, not arbitrary provider
responses. There is no R2 access, holdout access, provider switch, model
promotion, paper activation or trading.

A source revision or rejected daily reconciliation requires an evidence-based
decision; the code must not silently exclude BNXUSDT or change the dataset.
Publishing a verified candidate needs a separately reviewed versioned config
and receipt, exact source/candidate hashes, immutable destination lineage,
R2 headroom and original completion-gate checks.

## Development and cloud validation

The offline candidate builder and its nine synthetic tests were recovered
from the verified GitHub local-work snapshot. Additional cloud tests cover
bounded requests, missing daily files, overlap conflict, source revisions,
authority/hash/main/manual/expiry gates and zero reader construction on denial.
Production archive availability is not inferred from those tests.
