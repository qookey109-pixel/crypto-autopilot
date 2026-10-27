# Shared research collection V0.1

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY.

The disabled successor `run_shared_signal_collection` connects public research
source requests and existing conditional R2 publication to one shared reservation.
It performs no work with the default disabled flag. An empty enabled selection
also performs no admission or external access.

The caller supplies the existing source configuration rows, exact run/slot
reservation, fresh account-wide usage, prepaid query meter, trusted authority
binding validator and S3 credentials. Only the three declared source identities,
URLs and parse modes from the current V0.2 configuration are supported. Every
source row is validated before admission; duplicates and changed routes stop.

## Operation sequence and bounds

1. Validate input identity, envelope, credentials and projected storage headroom.
2. Reserve centrally before source access or S3 construction. Duplicate/changed
   reservations are rejected by the existing gate and cannot restart acquisition.
3. Fetch selected sources sequentially, at most three GET attempts, each with a
   20-second timeout and a 500000-byte body bound. Default transport disables
   redirects. There is no automatic retry, login or prose-direction inference.
4. Reject malformed declared JSON, non-object JSON and malformed explicit forecast
   arrays before the legacy parser. HTML metadata and absent forecasts remain valid.
   Recheck binding and fresh budget before each request. Any source failure or
   evidence expiry stops publication; reports retain fixed reasons and charged
   usage, never raw transport exception values.
5. Preserve global forecast-ID deduplication/revision rejection across sources.
   Within-source conflicts return a controlled report with retained reservation.
   Bound serialized payload to 262144 bytes, manifest and pointer to 4096 each.
   Oversized evidence is rejected without truncation or S3 construction.
6. Reuse the existing admitted publication body: pointer preflight, conditional
   immutable writes, SHA-256 readbacks, then conditional latest-pointer update.

One envelope reserves the selected provider count, **3 Class A / 6 Class B** and
**270336 new bytes**. Actual writes may be smaller; the central reservation is
never refunded. D1 admission/query-controller costs remain in the separately
prepaid envelope supplied by the caller. The ordinary strict publication-only
API retains its provider=0/exact-byte contract.

## Engineering versus activation

The composition is implemented and disabled. It has no CLI, workflow, schedule,
environment credential loading or production cutover. The four-writer registry
correctly still reports the existing legacy routes as unverified. No caller may
use an enabled flag as a substitute for exact merged finite execution authority,
complete current writer coverage, independently fresh budget/headroom evidence
and durable prepaid query metering. Trusted transport injection must preserve the
same single-attempt semantics; arbitrary custom clients are not proven safe.

This change performs no real provider/R2/D1 request. It does not qualify a
strategy or activate Cloud Paper. The legacy scheduled collector must be cut
over under separately reviewed authority, including run/slot binding and
retirement of its unconditional pointer path.

The cloud test suite covers admission ordering, full source/publication flow,
restart replay, unknown coverage, acquisition failure, stale evidence,
unregistered/duplicate source routes, envelope mismatch, oversized publication,
redirect rejection, immutable conflict and forecast revision. Existing
publication tests continue to cover ETag pointer races and readback failures.
See [execution ledger](superpowers/plans/2026-10-26-shared-signal-collection.md)
and PR checks for exact RED/GREEN outcomes.

Review validation: CI run [40432651658](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40432651658) passed Python 3.12/3.13, Ruff and 1966 tests. This is engineering evidence only; operational provider, D1 and R2 access remain NOT_RUN.
