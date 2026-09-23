# Current Operations Status

Updated: 2026-09-23. This is the single human entrypoint for the current project checkpoint.

**PAPER / LIVE-PAPER ONLY.** The data pipelines and paper components exist; the current research results do not support model promotion or real trading. Finish operational verification and reconcile local work before expanding the research scope.

## Read and act from the right source

1. **Resolve `main` live at read time.** The checkpoint below was observed against `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51` after PR #478; it is a dated observation.
2. Use the exact versioned config, receipt and immutable run evidence for any execution decision. This document adds no authority.
3. Use [PROJECT_STATUS.md](PROJECT_STATUS.md) for governance and retired-stage lineage, [README.md](README.md) for the product map, and [AGENTS.md](AGENTS.md) for agent rules.
4. Use live [pull requests](https://github.com/qookey109-pixel/crypto-autopilot/pulls) and [Actions](https://github.com/qookey109-pixel/crypto-autopilot/actions) for moving operational state.

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
| Pages reliability | PR #478 merged; post-merge build succeeded | Natural schedule verification is still pending at the checkpoint. A build success is not a deployment or browser check. |

Core100 dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
Weekly Training remains scheduled with dataset/model-blob fingerprint deduplication. An exact match returns `NO_CHANGE`, with no retraining or R2 write. The verified baseline experiment fingerprint is `25b3178ce0d13052684d20b35a0e1f6949f0d97a5ac0c5b9e8f0a52d4d12f9c8`.

Detailed evidence:

- [Core100 lifecycle and threshold results](PROJECT_STATUS.md#current-lifecycle)
- [Pionex V0.2 completion receipt](research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json)
- [ZEC V0.3 completion](research/receipts/2026-09-21-zec-v0-3-development-completion-v0-1.json)
- [ZEC V0.4 completion](research/receipts/2026-09-21-zec-v0-4-development-completion-v0-1.json)
- [Live Paper coordinator V0.2](config/live_paper_run_coordinator_v0_2.json) and [slot claim V0.1](config/live_paper_run_claim_v0_1.json)

## Current work, in order

| Priority | Work | Completion evidence / boundary |
| --- | --- | --- |
| 1 | Verify the next natural Pages schedule and Health result after #478 | Record event, run ID, head SHA and conclusion. Do not substitute push/workflow_run or dispatch a replacement. |
| 2 | Reconcile the old local checkout with current main | Inventory each changed/untracked file; preserve recovery files; review differing bytes before migration. |
| 3 | Review Core100 fingerprint dependency coverage | Synthetic dependency checks and a new contract/baseline migration proposal; no new training or R2 execution authority. |
| 4 | Resolve the remaining PR review | At the September 23 observation, #477 was open at `45fe053ceee7579570d7adffa899e97e5068be88`; recheck live base/checks before an explicitly authorized merge. |
| 5 | Tidy historical Actions registrations | The [operating map](docs/GITHUB_ACTIONS_OPERATING_MAP.md) separates current workflow files, removed-file registrations and dynamic Dependabot. Preserve historical run evidence. |

The [technical-debt register](docs/TECH_DEBT_REGISTER_2026_09_17.md) remains the cleanup register. This checklist is its current navigation, not a second issue tracker. Large-module refactoring, new strategy families and new schedules stay deferred until the operational checkpoint is resolved. The 261-error type baseline is historical; fetch current CI visibility before quoting a current count or choosing another typing slice.

## Automation checkpoint — September 23

The [GitHub Actions operating map](docs/GITHUB_ACTIONS_OPERATING_MAP.md) contains schedule times, event chains and historical categories. Main has eight workflow files with cron declarations (11 expressions); seven are effective inside their versioned windows, while V0.12 is expired. API `active` is not execution authority.

At the 2026-09-23 06:32 UTC observation:

- post-merge [CI `35813605260`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605260), [CodeQL `35813605270`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605270) and [Freeze Guard `35813605239`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605239) succeeded;
- [Pages push `35813605262`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35813605262) built successfully, with deploy and browser-production skipped;
- the September 23 04:43 UTC Pages schedule was not present in the queried run list; the prior schedule `35710497715` was cancelled;
- latest Health schedule `35804367103` was failure at 00:58:51 UTC; no later Health schedule was observed;
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
