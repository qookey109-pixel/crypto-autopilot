# Shared research source and publication Implementation Plan

> For agentic workers: use superpowers:executing-plans inline; perform a fresh whole-branch review at the end.

**Goal:** Admit the existing research source requests and conditional R2 publication under one shared reservation.

**Architecture:** Add a disabled successor composition around existing collect_sources and SharedWriterR2Budget. Extract the existing admitted publication body into one private helper so both the strict publication-only API and the combined composition reuse identical immutable/readback/latest-pointer behavior.

**Tech Stack:** Python 3.12/3.13, existing urllib / budget / S3 adapters, GitHub-hosted CI only.

**Spec:** docs/SHARED_SIGNAL_PUBLICATION_V0_1.md; user VNext goal section 4. No current workflow cutover.

## Global Constraints

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY.
Default disabled: no admission, SDK construction, source request or credential lookup.
Existing three source IDs/URLs/parse modes only. Up to 3 single GET attempts, 20 seconds and 500000 response bytes each, redirects and retries disabled.
One envelope: enabled source count, 3 R2 Class A, 6 Class B, 270336 new bytes (262144-byte payload plus two 4096-byte metadata objects). The existing budget guard's per-object ceiling still applies.
No modification of the legacy active workflow, frozen evidence, strategy, provider equivalence, holdout or runtime activation authority.

## Review Focus

- Duplicate reservation after restart must stop before source/S3 work.
- Failed/malformed/oversized sources must not leak exception values or publish partial source results.
- Evidence expiry during acquisition must stop before the next request or S3.
- Unregistered/duplicate sources, credentials and envelopes must fail before admission.
- Immutable conflicts and pointer races must retain full admission and existing conditional publication semantics.

## Task 1 — one combined composition

Files: create src/crypto_autopilot/research/shared_signal_collection_v0_1.py and tests/test_shared_signal_collection_v0_1.py; modify the publication module only to extract its admitted body; add config/shared_signal_collection_v0_1.json.

Interface: run_shared_signal_collection(*, sources, run_id, reservation, guard, execute, query_meter, validate_binding, credentials, transport=None, execution_enabled=False) -> dict.
Sources are complete selected rows from the existing configuration, validated against the existing three declared identities. An empty enabled selection is a no-op before admission.
The new module performs admission, sequential metered acquisition, safe payload construction, bounded serialization, then shared publication. No source or S3 side effect may precede admission; no second reservation is made for publication.

- [ ] Write tests for disabled/no-source, admission ordering, full success counters, duplicate replay, rejected admission, source failure, expiry, unregistered source, wrong envelope and oversized publication.
- [ ] GitHub CI RED must fail assertions because the combined runtime is absent, with no local execution.
- [ ] Extract private _publish_objects without changing the strict existing API; implement the successor with one no-redirect transport and sanitized failure summaries.
- [ ] GitHub CI GREEN must pass the full suite, Ruff and all required governance checks; existing publication regression tests must still pass.
- [ ] Fresh whole-branch review, address material findings, verify exact head/base/checks, merge and inspect postmerge CI.

## Execution ledger

Ruling: use a short-lived remote GitHub branch and hosted CI instead of local skill workspace/scripts — binding CLOUD_ONLY forbids local files and terminal; commits and this ledger preserve the execution record.
Ruling: follow existing execution/merge authorization without another design approval — the user has explicitly requested continuous implementation and opted out of repeated approval.
Pre-flight: collection consumes only a shared admitted budget; publication-only API keeps exact bytes/provider=0 validation. The combined envelope is conservatively retained in full, never refunded.
Current state: tests first; no combined production implementation yet.
