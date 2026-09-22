# Open PR Triage — 2026-09-22

Repository `main` is authority and must be resolved live before every merge decision. Evidence basis for this V0.7 refresh: `28099bafdc3addee363933dab4a99a32ea76fc2c` after PR #448 merged. This SHA is historical review context, not a future latest-main claim.

This document is navigation only. It grants no workflow-dispatch, provider, R2, holdout, source-switch, promotion, order, or live-trading authority.

Machine-readable companion: `research/status/open-pr-triage-v0-7.json`.

## Current open backlog

At this reviewed snapshot the GitHub open pull-request backlog is **zero**.

No old Dependabot or typing branch is a current merge candidate. Any new pull request must be evaluated against live `main` and current freeze boundaries.

## Dependency and typing review outcomes

- #441 — closed as duplicate after the same narrow liquidation-sensitivity typing fix was rebuilt on current main and merged as #445.
- #326 — closed without merge. `boto3 1.43.93` requires `botocore>=1.43.93,<1.44.0`, so the old single-pin proposal was incoherent with the repository's `botocore==1.43.75`; the shared CI constraints path is also currently freeze-protected.
- #327 — closed as duplicate after current-main compatibility review and successful merge of #447 (`actions/cache v6.1.0`).
- #328 — closed as duplicate after current-main compatibility review and successful merge of #448 (`actions/download-artifact v8.0.1`), retaining fail-closed digest verification.
- #329 — closed without merge. Current-main rebuild #446 changed only `requirements/ci-constraints.txt` and was rejected by V0.10 Critical Path Freeze Guard run `35747058798`; the freeze was not bypassed.
- #330 — closed without merge. The blanket `actions/checkout v6 -> v7` proposal changed 77 workflow files across active, retired and frozen/authority-sensitive paths, so it was not rebuilt as one global PR.
- #331 — closed without merge. The proposal combined a major pyarrow runtime jump, expansion of the public compatibility contract, and a frozen CI-constraints mutation; pyarrow remains deferred for a dedicated compatibility/freeze review.

## Current maintenance lane

Dependency review for #326–#331 is complete for this snapshot. There is no dependency PR waiting for merge.

The current non-execution type-visibility count after #445 is **216 errors**. Previously listed first-lane candidates `toolkit/descriptive_context_v0_1.py`, `research/pionex_universe_v0_1.py`, and `research/strategy_scorecard_v0_1.py` are already at zero errors in the latest measured report and must not be redone.

The next useful type-debt target is `src/crypto_autopilot/binance_expansion_plan.py` (17 informational mypy errors in the measured report), subject to characterization tests and behavior-preserving explicit narrowing. Execution-sensitive Paper paths remain deferred.

## Work-inventory boundary

Remote GitHub branch state is not evidence about uncommitted files in a developer checkout. Local-only / dirty checkout state remains **UNVERIFIED_FROM_GITHUB**.

Do not delete or overwrite local work solely from this triage. Frozen receipts/configs/evidence remain unchanged.

## Review rules

- Historical CI from an old base is not current merge evidence.
- Dependency changes touching frozen bytes require a separately reviewed versioned authority; do not bypass Freeze Guard.
- Major action/runtime changes require explicit compatibility review and small current-main scope.
- Type-debt work must not reduce counts through blanket `Any`, blanket `# type: ignore`, or behavior changes made only for mypy.
- No item in this navigation grants provider, R2, holdout, source-switch, promotion, real-money order, or live-trading authority.
