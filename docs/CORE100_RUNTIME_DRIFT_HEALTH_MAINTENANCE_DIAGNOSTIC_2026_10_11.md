# Core100 V0.2 runtime-manifest drift and Health/Maintenance distinction — 2026-10-11

## Scope and immutable sources

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD. This is a **read-only review of existing GitHub Actions metadata and logs**. No Core100 run, R2 access, provider request, train, storage write, workflow dispatch, or Cron change was performed.

- [Authorized one-time V0.2 baseline Action #36110721415](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415) created **2026-09-25T08:02:02Z**, event `workflow_dispatch`, `run_attempt=1`, source commit `41c79994a82a30d938774ff540c97767c0ad01d6`, `train=success`.
- [Existing weekly scheduled comparator Action #37196295102](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37196295102) created **2026-10-04T10:43:33Z**, event `schedule`, `run_attempt=1`, source commit `642400a8ec35a8b2116121fdaae8c08c164bf245`, `train=failure`. The embedded report was written before the workflow intentionally exited nonzero.
- The weekly original evidence artifact `11301206291` is non-expired in GitHub metadata. This review used the **already accessible log report**, not a new artifact or R2 read.
- [Pure comparator source](../src/crypto_autopilot/training/fingerprint_v0_2_execution.py) `compare_fingerprints()` requires exact `git_blobs`, then `runtime_guard_fingerprint`, then **`runtime_manifest`**, and only then compares dataset and experiment fingerprints.

## Verbatim field values from the existing run reports

| Field | Baseline #36110721415 | Weekly #37196295102 |
|---|---|---|
| `status` | `PASS` | `REVIEW_REQUIRED` |
| `reason` | `ONE_TIME_AUTHORIZED_BASELINE` | `RUNTIME_CHANGED` |
| `dataset_fingerprint` | `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876` | **Identical** |
| `runtime_guard_fingerprint` | `c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79` | **Identical** |
| `experiment_fingerprint` | `12ff384302785645144832115114a88f726bcc4ce51caa56497bec1209c76ed7` | `6e014580e0b85135fc9f44b556e7773a81c200b29ad7dc3aa9555901b300fba6` |
| `dataset_partition_objects` | 14,274 | 14,274 |
| `dataset_rows` | 18,235,427 | 18,235,427 |
| `training_performed` | true (single authorized baseline) | **false** |
| `r2_writes_performed` | true (single authorized baseline) | **false** |
| `provider_requests_performed` | 0 | 0 |
| `holdout_accessed` | false | false |

The weekly run also reports `r2_access_performed=true` and `r2_reads_performed=true`, under that run's preexisting comparator authority. **This forensic review made zero additional requests.**

**Conclusion:** The validated comparator reached its exact `RUNTIME_CHANGED` branch, which means it detected a mismatch in the normalized runtime manifest while the compared source/guard checks had passed. The GitHub Actions job failed *by design* after reporting `REVIEW_REQUIRED`. The identical dataset fingerprint is not independent proof of full dataset immutability; it is the available report claim.

The contract's runtime manifest includes exact Python patch/cache tag, `ubuntu-latest` runner identity, Linux/kernel/libc/platform, sorted installed distributions, pip/install/build tools, and project version. The workflow currently requests Python `3.13` and GitHub `ubuntu-latest`, both moving selectors. These are plausible drift surfaces, **not a verified identification of the exact changed field**. Neither log printed both full normalized manifest values. Do not assert a specific Python patch/runner/package change or a profitability implication without authenticating the actual manifests under appropriate authority.

## Operational effect and safe next decisions

1. Keep **Core100 model quality `REJECT`** and existing V0.2 automatic no-retrain/no-write boundaries. Do not reinterpret `REVIEW_REQUIRED` as `NO_CHANGE`, `PASS`, or a temporary network outage.
2. Existing Research Automation Health V0.2 correctly reports a failed observed scheduled workflow. The Cloud Project Maintenance V0.1 also has an **independent** blocker: stale bot draft [PR #789](https://github.com/qookey109-pixel/crypto-autopilot/pull/789). These are distinct causes; resolving the stale draft cannot cure Core100 runtime drift.
3. Draft [PR #797](https://github.com/qookey109-pixel/crypto-autopilot/pull/797) moves stale-draft detection into the read-only Maintenance inspector and still exits nonzero when stale. It must not mask the Health alert or publish a misleading green run.
4. Any future response to `RUNTIME_CHANGED` should first review which full manifest fields changed using only separately authorized source evidence. A proposed pin of an exact Python patch, runner image and dependency inventory requires a **separate reviewed versioned contract and authority decision**; no automatic baseline re-bootstrap, threshold change, holdout, source switch or training is authorized by this diagnosis.

This review is evidence-only and is not an invitation to rerun #37196295102, which already completed attempt 1 with `REVIEW_REQUIRED`.
