# Shared-admitted Live Paper recovery Implementation Plan

> For agentic workers: use superpowers:executing-plans inline, with one fresh whole-branch review.

**Goal:** Integrate the existing compact/legacy recovery verifier with one shared budget and immutable result-seal-only writes.

**Architecture:** New disabled composition reuses SharedWriterR2Budget, BudgetedR2Store, R2PaperRunStore and recovery V0.2. It does not change the frozen/active legacy entrypoint or mark writer registration complete.
**Tech Stack:** Python 3.12/3.13, existing S3 proxy and shared D1 admission, GitHub Actions only.
**Spec:** User VNext goal section 4; config/live_paper_run_recovery_v0_1.json; this plan defines the bounded successor behavior.

## Global Constraints
CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY.
No workflow, CLI, schedule, provider access, D1 provisioning or production execution.
Default disabled before input/credential/query/SDK access.
Exact recovery writer ID; provider_requests=0, R2 Class A=8, Class B=64, new_bytes=16384.
Four namespace inventories: each must terminate within one page of at most four keys; any truncation stops before repair.
At most four conditional result-seal creates of at most4096 bytes; no state/tick/step/header/claim mutation.
Recheck authority, budget and time before every S3 call. Retain full admission after any failure; no retry/refund.

## Review Focus
- A truncated inventory must not masquerade as a complete audit.
- An existing or concurrently created seal must never be overwritten.
- Failed writes/readbacks and expiry retain attempted counters and sanitized REVIEW_REQUIRED.
- Missing tick, chain conflicts and unknown coverage cannot produce repair success.
- Reconstructed duplicate admission must prevent all SDK/S3 work.

## Task 1 — bounded admitted recovery
Create src/crypto_autopilot/paper/shared_run_recovery_v0_1.py,
tests/test_shared_run_recovery_v0_1.py,
config/shared_run_recovery_v0_1.json and docs/SHARED_RUN_RECOVERY_V0_1.md.
Interface: run_shared_run_recovery(*, run_id, reservation, guard, execute, query_meter, validate_binding, credentials, repair_missing_result_seals=False, execution_enabled=False)->dict.
Scope prefix is the existing paper-run-store/v0.1, no caller-selected arbitrary paths.
Tests use real existing coordinator/validator over in-memory S3; no local or cloud production input.
- [ ] Tests first: disabled, audit, compact/legacy missing-seal repair, missing tick, page truncation, conflicting create, partial failure, expiry, duplicate admission and invalid identity/envelope.
- [ ] Hosted CI RED: missing new composition assertions only.
- [ ] Implement admission before SDK, strict bounded inventory, conditional seal/readback adapter and safe reports.
- [ ] Hosted full suite GREEN incl Ruff/governance and unchanged recovery/publication regressions.
- [ ] Fresh review; material fixes via RED/GREEN; final exact-head/base/checks, authorized squash and postmerge verification.

## Execution ledger
Ruling: remote short-lived branch and hosted tests replace skill local workspace/commands because user forbids local files/terminal. Use existing continuous implementation/merge authorization; no repeated design menu.
Pre-flight: single task reuses existing verifier and budget interfaces; inspect actual R2 proxy so conditional puts are also metered.
Design choice: bounded complete namespace scan rather than an operator-supplied ID manifest; an incomplete manifest could hide forks/orphans. This costs fail-closed availability once any kind exceeds four objects; future indexed recovery is a distinct change, not permission to truncate.
Design choice: every new seal uses IfNoneMatch=* and readback. Existing legacy active writer is unchanged; production cutover and all-writer coverage remain unverified.
