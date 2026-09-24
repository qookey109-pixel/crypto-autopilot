# Current Operations Status

Updated: 2026-09-24. This is the single human entrypoint for the current project checkpoint.

**PAPER / LIVE-PAPER ONLY.** The data pipelines and paper components exist; the current research results do not support model promotion or real trading. Continue cloud operational verification before expanding the research scope. User policy since 2026-09-25: all project work uses GitHub/cloud sources; local files, local testing and local cleanup are excluded.

## Read and act from the right source

1. **Resolve `main` live at read time.** This checkpoint was refreshed at 2026-09-23 19:34 UTC / 2026-09-24 03:34 Asia/Taipei after PR #494 merged at main `c06b46b61f6a26c7a8130cfd82b7c3408e29ed67`; this is a dated observation, not a latest-main claim.
2. Use the exact versioned config, receipt and immutable run evidence for any execution decision. This document adds no authority.
3. Use [PROJECT_STATUS.md](PROJECT_STATUS.md) for governance and retired-stage lineage, [README.md](README.md) for the product map, and [AGENTS.md](AGENTS.md) for agent rules.
4. Use live [pull requests](https://github.com/qookey109-pixel/crypto-autopilot/pulls) and [Actions](https://github.com/qookey109-pixel/crypto-autopilot/actions) for moving operational state.
5. For scheduled checks or a new model, use the [continuation runbook](docs/PROJECT_CONTINUATION_RUNBOOK.md): startup sequence, work IDs, checkpoints, evidence fields and blocked-state handling.

The machine-readable [Current Operations V0.3](research/status/current-operations-v0-3.json) remains a versioned lifecycle/evidence companion. Its evidence-basis parent `9ffe30c8f0ab28bc3b2a95ae19de6938ed613dae` has semantics `REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION` and is **not** a latest-main claim. Its dated PR counts and type-debt values are historical snapshots, not live backlog queries. Likewise, [PR triage V0.7](research/status/open-pr-triage-v0-7.json) records the completed September 22 review; do not reopen its closed dependency batch.

## Checkpoint: what is complete and what is still closed

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> REAL TRADING CLOSED / LIVE-PAPER SEPARATELY AUTHORIZED`

| Area | Current evidence | What follows from it |
| --- | --- | --- |
| Core100 History | 10/10 governed shards complete | Do not reacquire history solely because model quality rejected. |
| Core100 Training | Run `34918219864`: workflow success, report PASS; 100 symbols, 14,274 partitions, 18,235,427 rows, 249,228 examples | Pipeline completion is verified; model acceptance is a separate result. |
| Core100 quality | REJECT; threshold replay `34936331199` found `supported_thresholds=[]` in 0.50–0.55 | Keep configured threshold and quality gates; no automatic promotion. |
| Pionex validation V0.2 | Run `35054729471`: COMPLETE / PASS; 197 markets, 682 partitions, 1,534 requests | The bounded materialization contract completed; complete multiyear coverage and Pionex training are not claimed. |
| ZEC V0.3 | Run `35573236145`: 256/256 cells complete; NO_ELIGIBLE_DEVELOPMENT_CANDIDATE | No champion; fresh confirmation remains unopened. |
| ZEC V0.4 | Run `35618367238`: 24/24 cells complete; NO_ELIGIBLE_DEVELOPMENT_CANDIDATE | One-shot development is finished; do not dispatch it again from its earlier preregistration text. |
| Live Paper | Explicit public-market-data simulation, persistence and slot claim contracts exist | Manual governed operation only; no automatic schedule/candidate selection or private exchange orders. |
| Pages / Health reliability | Natural Pages schedule `35843351924` succeeded on main `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51`; later natural Health schedule `35870216734` succeeded on main `5b4aa2a4903ad2b630f3bbd4b4117adcffe867bf` | Pages build / deploy / browser-production succeeded; Health reported `Overall: PASS`, `alerts: 0`, with the dashboard backstop HEALTHY. TD-010 acceptance is satisfied. |

Core100 dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
Weekly Training remains scheduled with dataset/model-blob fingerprint deduplication. An exact match returns `NO_CHANGE`, with no retraining or R2 write. The verified baseline experiment fingerprint is `25b3178ce0d13052684d20b35a0e1f6949f0d97a5ac0c5b9e8f0a52d4d12f9c8`.

Fingerprint V0.2 preparation found that V0.1 omits `features/advanced.py`. If the live dataset and latest pointer still match the old baseline, the active V0.1 runner can return `NO_CHANGE` even though that feature source changed. Production R2 was not read during this audit, so the condition is not confirmed against the current dataset. V0.2 remains `PREPARED_NOT_ACTIVE`; its runner and workflow were not changed. See the [fingerprint V0.2 review](docs/CORE100_TRAINING_FINGERPRINT_V0_2.md).

Detailed evidence:

- [Core100 lifecycle and threshold results](PROJECT_STATUS.md#current-lifecycle)
- [Pionex V0.2 completion receipt](research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json)
- [ZEC V0.3 completion](research/receipts/2026-09-21-zec-v0-3-development-completion-v0-1.json)
- [ZEC V0.4 completion](research/receipts/2026-09-21-zec-v0-4-development-completion-v0-1.json)
- [Live Paper coordinator V0.2](config/live_paper_run_coordinator_v0_2.json) and [slot claim V0.1](config/live_paper_run_claim_v0_1.json)

## Current work, in order

| Priority | Work | Completion evidence / boundary |
| --- | --- | --- |
| 1 | Pages / Health reliability checkpoint | TD-010 complete: Pages `35843351924` succeeded naturally, followed by Health `35870216734` with `PASS` and zero alerts. Continue normal monitoring; do not create substitute dispatch evidence. |
| 2 | Cloud-only continuation | Local reconciliation is EXCLUDED_BY_USER, not a pending cloud task. Preserve the historical receipt; do not inspect, synchronize, delete or request local files. |
| 3 | Core100 fingerprint V0.2 | PR #494 merged to main `c06b46b`; V0.2 remains PREPARED_NOT_ACTIVE: 31-file import closure split into 14 result-identity and 17 runtime-guard paths; synthetic proof confirms V0.1 misses features/advanced.py. Legacy migration is REVIEW_REQUIRED; do not change the active runner, train, or access R2 without a separate versioned authority. |
| 4 | PR delivery checkpoint | PR #494 merged at `c06b46b`; post-merge tests (3.12/3.13), CodeQL, build and Freeze Guard passed. Pages build passed; deploy and browser-production were skipped by path filters. Delivery branch was deleted. Recheck live PR heads, bases and checks before future delivery actions. |
| 5 | Tidy historical Actions registrations | The [operating map](docs/GITHUB_ACTIONS_OPERATING_MAP.md) separates current workflow files, removed-file registrations and dynamic Dependabot. Preserve historical run evidence. |

The [technical-debt register](docs/TECH_DEBT_REGISTER_2026_09_17.md) remains the cleanup register. This checklist is its current navigation, not a second issue tracker. Use the single [Work Item intake](.github/ISSUE_TEMPLATE/work-item.yml) for planning; issue state grants no authority. Large-module refactoring, new strategy families and new schedules stay deferred until their stated gates are met. The 261-error type baseline is historical; fetch current CI visibility before quoting a current count or choosing another typing slice.

## Automation checkpoint — September 23

The [GitHub Actions operating map](docs/GITHUB_ACTIONS_OPERATING_MAP.md) contains schedule times, event chains and historical categories. Main has eight workflow files with cron declarations (11 expressions); seven are effective inside their versioned windows, while V0.12 is expired. API `active` is not execution authority.

At the 2026-09-23 12:49 UTC observation:

- post-merge [CI `35813605260`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605260), [CodeQL `35813605270`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605270) and [Freeze Guard `35813605239`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605239) succeeded;
- [Pages push `35813605262`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605262) built successfully, with deploy and browser-production skipped;
- natural Pages schedule [`35843351924`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35843351924) ran on main `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51`; build, deploy and browser-production all concluded `success`, completing at 09:31:59 UTC;
- Health schedule [`35834552996`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35834552996) failed at 07:59:11 UTC, before the successful Pages schedule; its single alert was the previously cancelled Dashboard backstop. The later natural Health schedule [`35870216734`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35870216734) completed successfully at 13:53:43 UTC on main `5b4aa2a4903ad2b630f3bbd4b4117adcffe867bf`; its report was `Overall: PASS`, `alerts: 0`, and the dashboard backstop was HEALTHY;
- Resource Hub schedule `35824364991` was created at 05:54:26 UTC versus its nominal 01:13 UTC slot. This is delay evidence, not a confirmed diagnosis of GitHub's scheduler.

These are dated observations, not promises of current health. PR #478 preserves queued production runs and rejects stale/unchanged deployments; the queue holds at most 100 pending runs.

## Established reliability behavior

- PR #421 chains Research Signal Quality to successful same-repository main Signal completion. Exact verified `run_id + manifest_sha256 + generated_at_utc` reuse rechecks freshness; mismatches use full lineage verification. The daily fallback remains.
- PR #422 provides pinned Playwright Chromium desktop/mobile checks for PR builds and after real production deployments. Skipped production checks are not PASS evidence.
- PR #423 requires the Live Paper atomic slot claim `IfNoneMatch="*"` before a new provider call. Unresolved conflicts fail closed without automatic retry, expiry or takeover. The coordinator uses explicit manual workflow_dispatch only.

## Boundaries and historical navigation

- Budget: **0 USD/month**, FREE-ONLY.
- Mode: **PAPER / LIVE-PAPER ONLY**; private exchange APIs, real-money orders and real live trading remain closed.
- Replacement holdout `2026-08-28` through `2026-09-03`: **FROZEN_UNOPENED**.
- `source_switch_authorized=false`; Binance and Pionex evidence remain provider-separated.
- Preserve frozen configs/receipts and failed evidence. Do not restart completed acquisition/development from older prose or loosen a gate after seeing a rejected result.
- Keep secrets out of files/logs/chat; Render never receives R2 credentials.
- The September 22 [PR review record](docs/OPEN_PR_TRIAGE_2026_09_22.md), earlier handoffs and Current Operations V0.3 retain their historical evidence. Live GitHub state takes precedence for open PRs and runs.

## Cloud-only maintenance V0.1 — review checkpoint

Prepared 2026-09-25 against main `f9296aca33858c907b42e825db8a9d334df1986e`; resolve main live.
The [versioned maintenance contract](config/cloud_project_maintenance_v0_1.json)
and [preparation receipt](research/receipts/2026-09-25-cloud-project-maintenance-v0-1.json)
become effective only after reviewed main merge. They add a GitHub-hosted
completion listener to natural Health V0.2, no new cron. The original Health
workflow and its read-only policy remain unchanged.

- PR #496 contains the pure fingerprint V0.2 comparator; check its live head,
  checks and merge state. Its merge does not activate training or V0.2 cutover.
- The 25 removed-file registrations were disabled and individually read back
  online. PR #497 records that completed operation; recheck its live merge state.
  Do not repeat disablement from older prose.
- CLOUD-01 / CLOUD-02 in the [continuation runbook](docs/PROJECT_CONTINUATION_RUNBOOK.md)
  are the bounded delivery and failure work cards. Existing Work Item intake remains
  the only issue system; maintenance does not create or label issues.
- All development and validation for this delivery take place on GitHub. No local
  recovery or dataset files are inputs. Standard GitHub-hosted temporary checkouts
  are cloud execution environments.
- Automatic repair is limited to the marked blocks in this file and the runbook.
  Program defects get an actionable handoff; draft PRs never merge automatically.
- Acceptance remains **WAITING_REVIEW_MERGE_AND_TWO_NATURAL_RUNS**, including
  a verified NO_CHANGE run with zero commits. CI success alone does not close it.
- Current Operations V0.3 research lifecycle remains unchanged; its new maintenance
  pointer is navigation, not execution or model authority.

<!-- cloud-maintenance:v0.1:begin -->
PENDING_FIRST_CLOUD_OBSERVATION
<!-- cloud-maintenance:v0.1:end -->
