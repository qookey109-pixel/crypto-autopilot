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

- [x] Write tests for disabled/no-source, admission ordering, full success counters, duplicate replay, rejected admission, source failure, expiry, unregistered source, wrong envelope and oversized publication.
- [x] GitHub CI RED must fail assertions because the combined runtime is absent, with no local execution.
- [x] Extract private _publish_objects without changing the strict existing API; implement the successor with one no-redirect transport and sanitized failure summaries.
- [x] GitHub CI GREEN must pass the full suite, Ruff and all required governance checks; existing publication regression tests must still pass.
- [x] Fresh whole-branch review and material findings addressed with cloud RED/GREEN.
- [ ] Verify final exact head/base/checks, merge and inspect postmerge CI.

## Execution ledger

Ruling: use a short-lived remote GitHub branch and hosted CI instead of local skill workspace/scripts — binding CLOUD_ONLY forbids local files and terminal; commits and this ledger preserve the execution record.
Ruling: follow existing execution/merge authorization without another design approval — the user has explicitly requested continuous implementation and opted out of repeated approval.
Pre-flight: collection consumes only a shared admitted budget; publication-only API keeps exact bytes/provider=0 validation. The combined envelope is conservatively retained in full, never refunded.
RED verified: head 4dd87c236aa084ba210724ba4237f12633ff0791, job 121637332164 ran 1962 tests and failed exactly the 10 new missing-runtime assertions. Existing tests introduced no additional failures.
Initial GREEN verified at ffd53d0ae68f0834fab0a910890b04b8b76f15de, job 121642666203: Ruff and 1963 tests passed. Legacy publication behavior retained through a shared private helper.
Ruling: publication envelope is 270336 bytes, lower than the legacy 2500000-byte planned maximum, because the existing shared guard limits each object to 262144 bytes; oversized payloads stop before S3 rather than increasing that ceiling.

Compatibility RED verified at head 930c1b56357499abfc3b40279e5acf1412b8b0f0, job 121640895496: 1963 tests, exactly one failure (cross-source forecast-ID revision incorrectly PUBLISHED). Initial ten tests and existing publication regressions passed. Restore existing global deduplicate_kol_forecasts before serialization; this preserves the legacy collector's conflict semantics.

Fresh whole-branch review: two Important findings accepted after reading the actual legacy parser: malformed declared JSON was silently treated as metadata, and within-source forecast revision escaped the controlled report. Both are successor-only fixes; the active legacy collector is unchanged.
Review RED verified at 23ceca03b67004bcfa7e448f23c9532e021b2599, job 121953361882: 1965 tests, exactly five failures (four malformed JSON subcases and one controlled-report escape). No other failures.
Fix pass: validate declared JSON object/explicit forecast-list structure before legacy parsing; catch collection-level conflicts into sanitized REVIEW_REQUIRED with retained admission and attempted counters. HTML metadata and absent forecasts stay supported.
Review limitations: real provider behavior, credentials, D1/R2 charges and operational writer coverage remain unverified production prerequisites; custom transport injection is a trusted boundary, not a proven production transport.
Review fix GREEN: head d23402ffc26e0e7a541df3ce6cba8a4b9cc1e6d6, CI run 40432651658, Python 3.12 job 121953802289: Ruff and 1966 tests passed, including malformed JSON, within-source conflict and legitimate HTML metadata. Python 3.13, workflow-static, dependency security and CodeQL also succeeded.
Integration ruling: use the user's existing explicit merge authorization and cloud-only GitHub squash path; no local merge/worktree/menu is applicable. Final metadata/evidence commit is checked again before merge; postmerge results remain separate.
Current state: implementation and review verified; final integration pending. No workflow cutover or external diagnostic performed.
