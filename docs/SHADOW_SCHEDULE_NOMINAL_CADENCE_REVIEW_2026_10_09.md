# Prospective Shadow — nominal UTC cron arrival review V0.1

**Evidence date:** 2026-10-09, Asia/Taipei. **Execution boundary:** CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER; ZERO USD; read-only metadata and pure tests. This report grants **no** extra GitHub schedule, workflow dispatch, artifact collection, provider requests, R2/D1, training, holdout, model promotion or trading.

## Verified inputs and meaning

- Repository authority was resolved to actual latest `main` prior to the PR. The original, unchanged workflow `.github/workflows/prospective-shadow-collection-v0-1.yml` has UTC `17 */4 * * *` with `cancel-in-progress: false` and bounded public-provider research-only collection.
- Nine **existing natural `schedule` workflow runs** from 2026-10-06 through 2026-10-09, each completed `success`, source branch `main`, attempt 1, and each `collect` job `success`, were read using GitHub REST workflow-run plus run-jobs metadata. Their original nine research ZIP archive digests, source SHA and content continuity were **separately** checked in [Cloud-only Action #37895797841](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37895797841), not by this pure metadata code. Nine valid research reports, 8,604 identical cross-batch candles, and five capture intervals exceeding six hours remain `REVIEW_REQUIRED`, not market readiness.
- This PR adds the dated [bounded run/job metadata snapshot](../research/status/prospective_shadow_schedule_arrival_snapshot_2026_10_09_v0_1.json), a **pure** fail-closed analyzer `src/crypto_autopilot/research/shadow_schedule_cadence_v0_1.py` and regression tests. No API call is made by the analyzer, and the checked-in snapshot is **not** an automatically updated feed or complete historical inventory claim.
- An arrival-time **candidate bucket** is simply the four-hour interval beginning at the **nearest preceding UTC `:17` cron anchor**. An actual run `created_at` does **not** contain the original scheduled trigger timestamp, so its bucket **cannot be authenticated as the intended cron slot**. An apparent 61–212 minute phase relative to an anchor is **not** GitHub queue-delay measurement. `run_started_at` matching `created_at` does not establish internal scheduled-event enqueue time.

## Dated bounded result

| Diagnostic | Result | Interpretation |
|---|---:|---|
| Existing natural runs and successful collector jobs | **9** | Verified run records, not 9 consecutive intended triggers |
| Candidate four-hour arrival windows, from 2026-10-06 16:17 UTC through 2026-10-09 04:17 UTC inclusive | **16** | A *bounded nominal-window grid*, not 16 proven dispatched events |
| Candidate windows with a recorded run creation | **9** | Descriptive grouping only, not authenticated slot assignment |
| Candidate windows with no recorded run creation | **7** | No observed `created_at` in those buckets; NOT seven proven dropped/missed triggers |
| Phase of a run creation after preceding cron anchor | **61–212 minutes** | Not an actual queue/dispatch delay estimate |
| Observed run-to-run intervals above six hours | **5** | Arrival gaps 372, 571, 527, 571 and 529 minutes; continuity review required |
| Observation warmup | **9 / 21** | Insufficient, temporally interrupted; 30–90-day prospective edge not proven |

**Seven candidate buckets without an observed creation (UTC):** 2026-10-07 00:17, 08:17, 16:17; 2026-10-08 00:17, 08:17, 16:17; 2026-10-09 00:17.

These seven are *not equal* to five observed interarrival gaps: the former counts empty nominal arrival buckets, the latter counts **pairs** of run creations separated by over six hours.

**All nine actual `collect` jobs reported success.** Accordingly, the five gaps cannot be attributed to a verified collector-job failure. Whether individual cron events were queued late, dropped, never dispatched, or omitted from bounded retrieval remains **UNKNOWN**. GitHub's [official Actions documentation](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows) says scheduled events can be delayed under high load and some queued jobs can be dropped; those are possible platform behaviors, not identified root causes for these particular runs.

## Relationship to the already-merged reference-grid receipt

The existing merged `research/receipts/2026-10-09-shadow-nine-run-cron-grid-v0-1.json` and `shadow_cron_grid_diagnostic` count **15 nominal UTC reference points strictly inside the interval between the first and last run creation timestamps**. This V0.1 diagnostic instead counts **16 inclusive four-hour candidate arrival buckets**, from the nearest prior cron reference before the first run to the nearest prior reference before the last run, of which **seven contain no run creation**. These are different counting conventions for different objects, **not inconsistent evidence and neither represents missed trigger count**. This companion additionally checks the independent successful `collect` job result on each existing run, which the original pure grid function did not attest.

## Guardrails and next check

1. Do **not** backfill any gap, attach a fabricated intended-slot ID, rerun the research collector, adjust UTC cron, or set `github_schedule_changes_authorized=true` based on this review.
2. At the next authorized **read-only** check, capture and correlate run metadata, collection report and exact run/attempt/source SHA for each new original artifact; distinguish no record in GitHub REST from an actual failed workflow.
3. Keep `Core100 REJECT`, `REGIME_UNAVAILABLE`, Cloud Paper `NOT_WIRED / NOT_RUN / NOT_CONFIGURED`, source switch and all live-money execution disabled. This is **metadata forensics only**.
