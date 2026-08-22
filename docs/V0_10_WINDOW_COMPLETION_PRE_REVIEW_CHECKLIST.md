# V0.10 Window Completion Pre-Review Checklist

Status: **PREPARED / NOT EXECUTION AUTHORITY**

This checklist is for the first read-only review **after** the frozen metadata capture window has fully ended at `2026-09-04T01:59:59.999Z` and **before** any separate V0.11 production-evaluation authority is drafted or any production R2 receipt is listed/read.

It is not a metadata-stability evaluation and cannot produce a stability PASS or FAIL from production R2 evidence.

## Allowed evidence for this pre-review

Only read-only operational lineage may be inspected:

- current Repository `main`, `PROJECT_STATUS.md`, commit history and diffs;
- the frozen V0.10 critical-path manifest / guard results;
- GitHub Actions V0.10 scheduled workflow run/job/step metadata;
- GitHub Actions observer run/job/step metadata;
- any versioned emergency authority that was actually merged during the window;
- Render service/deploy metadata in read-only mode.

Do **not** list/read production R2, read capture artifacts, query providers, read Render provider payloads, or access replacement holdout data during this checklist.

## Review sequence

1. Confirm the full capture window has ended. If it has not ended, stop with `NOT_YET_REVIEWABLE_WINDOW_STILL_OPEN`.
2. Re-read current `main` and `PROJECT_STATUS.md`; do not use a stale chat state as authority.
3. Confirm `main` protection and required CI state are still intact.
4. Compare the frozen V0.10 critical-path baseline `4a805b30183b23e29ea36689dfaa2ba0a4e4533f` to the post-window `main`.
5. For every production-critical diff, require a versioned emergency authority and protected-main lineage. Unreviewed critical-path drift stops the review.
6. Enumerate V0.10 scheduled workflow run lineage from GitHub metadata. Preserve failed, cancelled, skipped or missing attempts exactly as observed; do not backfill them.
7. Review observer failures / pipeline-health warnings. Observer PASS is operational only and is not capture-evidence PASS.
8. Verify Render service/deploy lineage read-only. Do not deploy or alter environment values.
9. Verify holdout, source switch, W1, backtest/strategy and trading boundaries remain closed.
10. Emit only one pre-review state and stop. Do not construct an R2 client.

## Allowed pre-review states

- `PRE_REVIEW_COMPLETE_READY_FOR_SEPARATE_V0_11_AUTHORITY_DECISION`
- `STOP_UNREVIEWED_CRITICAL_PATH_DRIFT`
- `STOP_SAFETY_OR_AUTHORIZATION_BOUNDARY_VIOLATION`
- `NOT_YET_REVIEWABLE_WINDOW_STILL_OPEN`

The READY state means only that a **separate versioned V0.11 production-evaluation authority may be considered**. It does not authorize that evaluation and does not imply that 194 valid R2 receipts exist.

## Non-negotiable boundaries

Missing or failed GitHub attempts remain evidence and may not be repaired, hidden, re-timestamped or retroactively backfilled. This checklist cannot authorize manual V0.10 capture, production R2 access, holdout access, provider requests, source switching, W1 materialization, backtest admission, strategy changes, real-money orders or live trading.

A future V0.11 production evaluation may begin only after the full window ends and after a separate protected-main authority is created and merged under the already-prepared V0.11 authority template.
