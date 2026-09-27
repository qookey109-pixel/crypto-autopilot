# 2026-09-27 Natural Schedule Acceptance Checklist

Prepared on 2026-09-26 against main `fd68650472188e6cdded4d4e6aa5b1a452774f72`.

This document is an observation checklist, **not execution authority**. Before acting, re-resolve live `main`, open pull requests, workflow source, and exact run metadata. Do not use manual dispatch to substitute for missing natural schedule evidence.

## Purpose

The next fixed checkpoint is the 2026-09-27 natural Pionex observability and Core100 Weekly Training sequence. Keep the runtime baseline stable until those runs are reviewed. In particular, do not edit:

- `src/crypto_autopilot/paper/live_v0_1.py` execution-chain typing paths;
- `src/crypto_autopilot/training/detailed.py`;
- the Pionex observability workflow/config/authority;
- the Core100 Weekly Training workflow/fingerprint contract;
- thresholds, promotion gates, source-switch authority, holdout state, or live-trading authority.

The current type-visibility baseline is 33 diagnostics: 18 protected and 15 ordinary cleanup candidates. The 15 ordinary candidates are the five remaining Live Paper execution-chain diagnostics plus ten `training/detailed.py` diagnostics. Natural evidence review is necessary but not sufficient to resume a slice. The visibility label "ordinary" does not mean fingerprint-independent: `src/crypto_autopilot/training/detailed.py` is explicitly listed in the active V0.2 successor contract's `identity_contract.code_paths`. Keep its ten diagnostics deferred until a separately reviewed fingerprint-impact decision exists. Recheck the five Live Paper diagnostics against current receipt, identity, runtime-guard and dependency bindings before selecting any bounded change.

## Current pre-check evidence

| Item | Latest reviewed natural evidence before this checklist | Interpretation |
| --- | --- | --- |
| Pages | Run `36232991943`, schedule, success, head `fd68650472188e6cdded4d4e6aa5b1a452774f72` | Current-main scheduled dashboard pipeline completed successfully. |
| Research Automation Health | Run `36228511162`, schedule, success | Latest reviewed Health schedule was healthy; do not dispatch a replacement for later missing slots. |
| Pionex observability | Run `35500652150`, 2026-09-20 schedule, success | Prior bounded observability evidence exists; 2026-09-27 remains the next fixed natural checkpoint. |
| Core100 weekly | Run `35502249846`, 2026-09-20 schedule, success under the previous workflow display name | Historical weekly evidence only. The 2026-09-27 run must be evaluated against the current V0.2 successor implementation. |
| Core100 V0.2 bootstrap | Run `36110721415`, workflow_dispatch, success | One-time bootstrap is consumed; it must not be rerun. Model quality remains separate and rejected. |

## Nominal 2026-09-27 sequence

Times are Asia/Taipei. GitHub schedule delivery can be delayed; the nominal time is not a completion deadline.

| Nominal time | Workflow | Required evidence |
| --- | --- | --- |
| 11:53 | Pionex Alternative Assets Observability V0.2 | Natural `schedule` event, exact head SHA, run/attempt, job conclusion, secret-free report artifact, report status and safety-boundary fields. |
| 12:37 | Binance USD-M Crypto Core 100 Training V0.2 | Natural `schedule` event, exact head SHA, run/attempt, report artifact, fingerprint comparison result, training/R2/provider flags. |
| 12:43 | Dashboard GitHub Pages | Record whether the natural schedule ran and whether build/deploy/browser-production actually executed; skipped jobs are not PASS evidence. |
| 12:57 | Research Automation Health V0.2 | Natural schedule result, exact head, overall result, alert count and schedule coverage. |
| after Health | Cloud Project Maintenance V0.1 | Only a same-repository natural Health schedule may trigger it. Record inspect/propose result or NO_CHANGE; do not manufacture replacement evidence. |

## Pionex acceptance

Record:

- run ID and attempt;
- event = `schedule`;
- exact `head_sha`;
- workflow/job conclusion;
- artifact ID/name;
- report `status`;
- `catalog_validation_status`;
- `catalog_diff_status`;
- `provider_requests_performed`;
- R2 latest-pointer/readback result;
- authority/safety-boundary booleans.

Interpretation:

- `PASS`: record the bounded evidence; this does not authorize source switch, model promotion, trade plans, orders, or live trading.
- `REVIEW_REQUIRED`: preserve the report and review the concrete catalog validation and/or catalog-diff reason; do not widen scope automatically.
- `SKIPPED`: verify the window/guard reason and confirm zero provider requests and no R2 access. Do not manually rerun merely to replace natural evidence.
- workflow failure: preserve the failed run and classify the concrete failure before any code change.

The existing V0.2 schedule window expires 2026-10-01 08:00 Asia/Taipei. No automatic extension is authorized.

## Core100 Weekly Training acceptance

Record:

- run ID and attempt;
- event = `schedule`;
- exact `head_sha`;
- report artifact ID/name;
- dataset fingerprint;
- experiment/model fingerprint;
- runtime guard fingerprint where present;
- report `status`;
- `training_performed`;
- `r2_writes_performed`;
- `provider_requests_performed`;
- model-quality result, if emitted.

Interpretation:

- `NO_CHANGE`: require `training_performed=false`, `r2_writes_performed=false`, and `provider_requests_performed=0`. This is the expected deduplication path only if the governed fingerprints are unchanged.
- `PASS`: preserve the report and treat it as unexpected for the current comparison-only natural schedule. The active successor contract has `scheduled_retraining=false`; the consumed bootstrap does not authorize another training run or R2 write. Inspect the report and current authority before any follow-up; do not rerun or infer model acceptance.
- `REVIEW_REQUIRED`: stop for review; do not loosen a gate or rerun until the reason is understood.
- `SKIPPED`: confirm the explicit guard reason and zero unauthorized activity.

Do not rerun the consumed V0.2 bootstrap. Do not infer promotion, threshold change, source switch, holdout opening, or live trading from workflow success.

## Manual supplemental verification — 2026-09-27

The nominal Pionex/Core100 natural schedule slots had not appeared in the Actions schedule feed when rechecked after their expected time. Two operator-initiated `workflow_dispatch` runs were then executed only as supplemental runtime verification. **They do not satisfy or replace the natural schedule rows in the decision ledger below.**

| Workflow | Manual run | Exact head | Workflow result | Report interpretation |
| --- | --- | --- | --- | --- |
| Pionex Alternative Assets Observability V0.2 | `36299696477`, attempt 1 | `fd68650472188e6cdded4d4e6aa5b1a452774f72` | SUCCESS | Report `REVIEW_REQUIRED`; catalog diff `PASS`; validation `REVIEW_REQUIRED`; 80 matched markets from 125 frozen registry candidates; 0 added / 0 removed; 62 unresolved X-suffix symbols were review-only and not selected. |
| Binance USD-M Crypto Core 100 Training V0.2 | `36299706656`, attempt 1 | `fd68650472188e6cdded4d4e6aa5b1a452774f72` | SUCCESS | Report `SKIPPED` with reason `MANUAL_DISPATCH_WITHOUT_BOOTSTRAP_INPUT`; training=false; provider requests=0; R2 access/reads/writes=false; consumed bootstrap was not rerun. |
| Dashboard GitHub Pages (follow-up) | `36299744851` | `fd68650472188e6cdded4d4e6aa5b1a452774f72` | SUCCESS | Triggered by `workflow_run` after manual Pionex. `build=success`, `deploy=success`, `browser-production=success`; deployed desktop/mobile browser validation passed. This is current-main event-driven production evidence, not the missing natural 12:43 schedule evidence. |

### Pionex manual-review classification

The Pionex workflow itself completed successfully and the prior-catalog comparison did **not** detect a material catalog change: `catalog_diff_status=PASS`, `added_count=0`, and `removed_count=0`.

The report remained `REVIEW_REQUIRED` because the frozen validation contract treats live Pionex symbols whose base ends in `X` but is not present in the explicit registry as review-only. The supplemental run observed `unresolved_x_suffix_count=62`. Those symbols were not auto-classified, not added to the registry, and not selected as alternative assets. This is a fail-closed classification boundary, not evidence of a catalog-diff failure.

The manual Pionex run performed one public symbol-metadata request and published bounded catalog evidence to R2 with latest-pointer-last/readback protections. It did not authorize historical materialization, training, model promotion, trade plans, private API use, real-money orders, source switching, or live trading.

### Natural evidence still pending

At the last recheck, the Actions schedule feed for 2026-09-27 still contained the earlier natural Research Automation Health run `36284094605`, but no 2026-09-27 natural Pionex or Core100 run for the nominal midday slots. Keep the natural decision-ledger rows pending until GitHub emits qualifying `event=schedule` runs or the missed-slot observation is formally closed without substituting manual evidence.

## Follow-up acceptance

After Pionex and Weekly Training:

1. Re-resolve `main` and verify the natural runs belong to the intended default-branch state.
2. Review Pages separately: build, deployment and browser-production each need their own conclusion.
3. Review the subsequent Health natural run. Preserve delayed/missing slots as observations instead of replacing them with dispatch evidence.
4. Review Cloud Maintenance only if it was triggered by the qualifying natural Health run.
5. Update status documentation with exact run IDs, attempts, head SHAs and artifact IDs.
6. Only then review eligibility for the five Live Paper execution-chain diagnostics. Keep the ten `training/detailed.py` diagnostics deferred because the file is experiment-identity-bound; natural acceptance alone does not remove that binding.

## Decision ledger

| Check | Run ID | Head SHA | Result | Artifact / evidence | Next action |
| --- | --- | --- | --- | --- | --- |
| Pionex 11:53 | no qualifying natural run observed as of 2026-09-27 14:29 Asia/Taipei | `fd68650472188e6cdded4d4e6aa5b1a452774f72` expected default-branch baseline | `MISSING / DELAYED / UNKNOWN` | manual supplemental run `36299696477` is recorded above but is not natural evidence | keep the natural slot unresolved; do not relabel manual evidence |
| Core100 12:37 | no qualifying natural run observed as of 2026-09-27 14:29 Asia/Taipei | `fd68650472188e6cdded4d4e6aa5b1a452774f72` expected default-branch baseline | `MISSING / DELAYED / UNKNOWN` | manual supplemental run `36299706656` was `SKIPPED` safely and is not natural evidence | keep the natural slot unresolved; do not infer NO_CHANGE |
| Pages 12:43 | no qualifying daily natural schedule observed as of 2026-09-27 14:29 Asia/Taipei | `fd68650472188e6cdded4d4e6aa5b1a452774f72` expected default-branch baseline | `MISSING / DELAYED / UNKNOWN` | workflow-run Pages `36299744851` succeeded after manual Pionex, but is event-driven rather than the daily schedule | keep natural schedule observation separate from event-driven success |
| Health 12:57 | no later qualifying natural Health run observed as of 2026-09-27 14:29 Asia/Taipei | `fd68650472188e6cdded4d4e6aa5b1a452774f72` | `MISSING / DELAYED / UNKNOWN` | latest 2026-09-27 natural Health remains run `36284094605` from 08:58 Asia/Taipei | preserve the missing/delayed observation |
| Cloud Maintenance | no qualifying new trigger after the unresolved midday Health slot | `fd68650472188e6cdded4d4e6aa5b1a452774f72` | `NOT TRIGGERED FROM QUALIFYING NEW NATURAL HEALTH` | earlier natural chain `36284094605` → `36284116625` succeeded; no manual substitute accepted | wait only for a qualifying natural Health completion |

## Observation checkpoint — 2026-09-27 14:29 Asia/Taipei

A live recheck at `2026-09-27 14:29:42+08:00` still showed `main=fd68650472188e6cdded4d4e6aa5b1a452774f72`. The 2026-09-27 schedule feed still exposed only natural Health run `36284094605` for the date; no qualifying Pionex 11:53, Core100 12:37, daily Pages 12:43, or later Health 12:57 natural run was visible at that checkpoint.

Per the repository operating map, this is recorded as `MISSING / DELAYED / UNKNOWN`, not as a scheduler-failure diagnosis and not as acceptance success. Manual and workflow-run evidence remain useful runtime evidence but stay separate from the natural-schedule acceptance claim.


## Audit follow-up — 2026-09-27 14:45 Asia/Taipei

Mode: `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`. Reviewed main remains `fd68650472188e6cdded4d4e6aa5b1a452774f72`. This section adds observations and review blockers; it does not close natural acceptance.

### Local-day coverage and Health freshness

The earlier 14:29 observation is retained as history. Its statement about the September 27 feed must not be interpreted as complete Asia/Taipei-day coverage. A Taipei calendar day starts at 16:00 UTC on the preceding date.

At the 14:43 recheck, the repository Actions API query used `event=schedule`, `created>=2026-09-26T16:00:00Z`, and `per_page=100`: one page returned all four records (`total_count=4`).

| Natural run | Created UTC | Created Asia/Taipei | Result |
| --- | --- | --- | --- |
| Health `36261294774` | 2026-09-26 18:05:09 | 2026-09-27 02:05:09 | SUCCESS |
| Health `36273577136` | 2026-09-26 21:37:32 | 2026-09-27 05:37:32 | SUCCESS |
| Health `36284094605` | 2026-09-27 00:58:11 | 2026-09-27 08:58:11 | SUCCESS |
| Resource Hub `36300466626` | 2026-09-27 06:33:54 | 2026-09-27 14:33:54 | SUCCESS |

No Pionex, Core100, or daily Pages natural run was present in that complete returned interval. Nominal-slot assignment for Health remains UNKNOWN where the run metadata cannot identify the original cron occurrence; do not assign each run to the nearest slot.

At `2026-09-27T06:45:23Z`, the latest natural Health run's verified `run_started_at=2026-09-27T00:58:11Z` was 20,832 seconds old (5h 47m 12s). Current `config/research_automation_health_v0_2.json` allows 14,400 seconds, and `src/crypto_autopilot/research/automation_health.py` evaluates age from `run_started_at` first. Applying that existing policy gives **STALE** at this observation. This is a metadata-derived current freshness finding, not a new Health report or a diagnosis of GitHub scheduler failure. The earlier run's historical SUCCESS is preserved. The Health-dependent Maintenance listener cannot independently wake when Health does not run.

### PR review blockers

- PR #533 head `746459127d1692a6f47ef562bb725e68d307ace6` has zero check runs and five pull-request workflow runs with conclusion `action_required`: `36261391901`, `36261391908`, `36261391902`, `36261391903`, and `36261391918`. Classification: **WAITING_CI_APPROVAL**, not PASS. GitHub documents the approval requirement for PR events generated with `GITHUB_TOKEN`: [Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
- #533 changes only the two generated maintenance blocks in `CURRENT_STATUS.md` and the continuation runbook; #532 adds this separate checklist. They do not directly overwrite the same file. Review snapshot freshness and CI before disposition; do not close or merge solely because one snapshot is older.
- #533's source Health `36261294774` was created September 27 at 02:05 Asia/Taipei, although its UTC date is September 26.
- #534 remains Draft. Its PR build/checks passed, while PR `deploy` and `browser-production` were SKIPPED; those skips are not production validation of the proposed UI.

### Bounded follow-up order

1. Resolve the Health freshness alert using a later qualifying natural run and its actual result; preserve this stale interval. Keep Pionex/Core100 natural acceptance unresolved until evidence review or an explicit documented missed-observation closure decision.
2. Correct documentation/readiness classifications before resuming engineering work. Fingerprint-bound training cleanup stays deferred.
3. Review Pionex failure-evidence retention after the current natural observation closes. The artifact-upload step lacks a failure condition, so a post-run assertion failure can skip upload even when a report exists; cleanup then removes runner output. If the Python entrypoint fails earlier, it currently may not write a report at all, so changing upload to `always()` alone does not solve that case. Design a secret-free, side-effect-aware failure report and upload behavior under a separate bounded review. This is a code-review finding, not a failure observed in today's successful manual run; any fix requires the existing authority/binding review and cloud regression.
4. Continue the existing seven-day observation through September 30 at 20:49 Asia/Taipei (168 hours from September 23 at 20:49). A preliminary query at this audit returned all 32 natural runs since `2026-09-23T12:49:00Z` on one 100-row page, all with workflow conclusion SUCCESS. That count is not slot coverage or proof of healthy freshness; missing slots, ambiguous assignments and queue/duration data still need review.
5. On October 1 after 08:00 Asia/Taipei, review Pionex expiry under the existing authority. These are review checkpoints, not newly installed schedules. Existing cron expressions remain unchanged.

## Follow-up — 2026-09-27 15:11 Asia/Taipei

A fresh GitHub read found main still at `fd68650472188e6cdded4d4e6aa5b1a452774f72`. The repository Actions query `event=schedule`, `created>=2026-09-26T16:00:00Z`, `per_page=100` returned `total_count=4` on one page: the same three natural Health runs and Resource Hub run listed above. No qualifying natural Pionex, Core100, or daily Pages run had appeared. The midday Health slot still lacks an identifiable qualifying run; nominal-slot attribution remains UNKNOWN. The latest observed natural Health remains `36284094605` from 08:58 Asia/Taipei, so the dated freshness concern remains open. Manual and event-driven runs do not close these natural observations.

The maintainer-approved PR #533 workflows have now run against exact head `746459127d1692a6f47ef562bb725e68d307ace6`. GitHub reports nine completed checks: seven successful (Python 3.12 and 3.13 tests, workflow-static, Pages build, Zh-Hant snapshot, CodeQL, dependency-security) and two skipped (PR Pages deploy and browser-production). The earlier `WAITING_CI_APPROVAL` statement remains an accurate 14:45 historical observation; its current classification for this head is `CI_COMPLETE_WITH_EXPECTED_PR_SKIPS`.

PR #533 changes only the generated maintenance blocks in `CURRENT_STATUS.md` and the continuation runbook, using an observation from 02:06 Asia/Taipei before the Pionex/Core100 checkpoints. PR #532 adds this separate, later checklist. Keep #533 Draft while the 9/27 natural schedule observation is unresolved; its bot may update the same branch after a later qualifying natural Health completion. The current maintenance publisher explicitly reuses an open draft with its branch prefix, and a closed PR with its branch retained stops at `CLOSED_BRANCH_REVIEW_REQUIRED`. Recheck the exact head, snapshot and CI before any later merge or closure. This PR review changes no cron, runtime or research authority.

## Boundaries

Budget remains FREE-ONLY / 0 USD per month. The project remains PAPER / LIVE-PAPER ONLY. Replacement holdout remains frozen and unopened. `source_switch_authorized=false`. Do not write secrets to repository content, logs, artifacts, or chat.
