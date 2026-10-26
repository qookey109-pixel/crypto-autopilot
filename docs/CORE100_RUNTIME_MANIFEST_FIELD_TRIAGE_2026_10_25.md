# Core100 V0.2 runtime drift — exact Runner evidence and no-access diagnostic (2026-10-25)

**Scope:** CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD/month / PAPER-LIVE-PAPER ONLY. Existing public GitHub Actions logs and pure synthetic unit tests only. No local file access, provider requests, R2 reads/writes, new GitHub training dispatch, holdout, promotion, source switch or real-money orders. This adds to—not edits—the 2026-10-11 [original diagnostic](CORE100_RUNTIME_DRIFT_HEALTH_MAINTENANCE_DIAGNOSTIC_2026_10_11.md).

## Exact immutable observations

| Existing completed job | Baseline | Weekly comparator |
| --- | --- | --- |
| Run (source job) | [#36110721415](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415), job `107993346383` | [#37196295102](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37196295102), job `111418765594` |
| Event / attempt | workflow_dispatch / 1 (authorized one-time baseline) | schedule / 1 (preexisting fingerprint check) |
| Workflow source SHA | `41c79994a82a30d938774ff540c97767c0ad01d6` | `642400a8ec35a8b2116121fdaae8c08c164bf245` |
| Job outcome | success | failure by fail-closed `RUNTIME_CHANGED` |
| CPython setup log | `3.13.15` | `3.13.15` |
| System family/OS | `ubuntu-24.04`, Ubuntu `24.04.5 LTS` | `ubuntu-24.04`, Ubuntu `24.04.5 LTS` |
| **Runner Image: Version** | **`20260920.314.1`** | **`20260927.320.1`** |
| Runner Image release link | [ubuntu24/20260920.314](https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260920.314) | [ubuntu24/20260927.320](https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260927.320) |
| setuptools installation log | `80.9.0` | `80.9.0` |
| Dataset fingerprint (reported) | `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876` | Identical |
| Runtime-guard fingerprint (reported) | `c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79` | Identical |
| Experiment fingerprint | `12ff384302785645144832115114a88f726bcc4ce51caa56497bec1209c76ed7` | `6e014580e0b85135fc9f44b556e7773a81c200b29ad7dc3aa9555901b300fba6` |
| Training / R2 writes | One-time authorized baseline performed | Both **false** |

The GitHub job setup log explicitly records a changed full image version while Python patch and logged setuptools versions are unchanged. Source [`fingerprint_collector_v0_2.collect_runtime_manifest`](../src/crypto_autopilot/training/fingerprint_collector_v0_2.py) includes the GitHub Actions `ImageOS` and `ImageVersion` environment variables under `runner_image` in the normalized runtime manifest; it also inventories Linux kernel, libc and installed distributions. The distinct logged runner versions therefore strongly indicate an expected source of normalized runtime drift. The actual complete baseline and weekly manifest objects have **not** been independently authenticated and compared in this review. Treat the specific root cause and other possible changed fields as **UNKNOWN**; do not assert that the image was the only change or relax a threshold to pass.

Current Health [#40165377547](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40165377547) remains ALERT due to the scheduled Core100 training failure. Maintenance [#40165410002](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40165410002) separately succeeded but does **not** clear training Health. The existing `Core100 Model Quality = REJECT` remains unchanged.

## Latest natural weekly check on 2026-10-25 (observed after initial PR)

[Core100 scheduled run #40180181401](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40180181401), job `121129383629`, source main `944895170f80af21e8f9b544ec42b279c45c0d6e`:

- GitHub runner image `ubuntu-24.04`, exact version **`20261012.334.1`**, as recorded in the job setup log.
- The `actions/setup-python` log reports **CPython `3.13.16`**, compared with the one-time baseline's **`3.13.15`**. The published Runner image and Python patch have both changed since that baseline; their exact manifest field impact and other differences remain unverified.
- The existing emitted JSON report records `status=REVIEW_REQUIRED`, `reason=RUNTIME_CHANGED`, `dataset_fingerprint=91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876` (matches baseline), `runtime_guard_fingerprint=c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79` (matches baseline), and `experiment_fingerprint=daa7a660e622fab400d3125ce8b11a030916a9335966119942766bce24ae4b43` (differs). Explicitly `training_performed=false` and `r2_writes_performed=false`; **`r2_access_performed=true` and `r2_reads_performed=true` belong to this preexisting scheduled comparator**, not the current retrospective read-only investigation. No provider calls were reported.
- This is a *newly observed actual failed natural run*, not additional authorized model training. Health can correctly remain ALERT even when other workflows and Maintenance succeed.

Unit tests additionally model two simultaneous **synthetic** differences (Runner image version and Python version), while preserving `runtime_changed_root_cause_proven=false` until separately authenticated full source manifests are available. This appendix is not an update to frozen baseline or a new execution grant.

## New purely local-to-the-GitHub-workflow diagnostic contract

`src/crypto_autopilot/training/runtime_manifest_field_review_v0_1.py` is a **pure function** over two complete caller-supplied V0.2 runtime manifests; it imports the pre-existing strict `normalize_runtime_manifest` function. It does not read any source files, network, environment variables, provider API or R2. It rejects missing/invalid manifest fields, produces only changed top-level field names and changed normalized distribution/tool **names** (not their raw values), and never confers source authentication, training authority or `NO_CHANGE` production semantics. All tests are synthetic and specifically assert these limitations.

The original immutable fingerprints, manifests, bootstrap, training workflow and model-quality gates are not modified. This module is **not wired into the scheduled training task**.

## Next protected decision

To identify exactly which normalized fields triggered `RUNTIME_CHANGED`, obtain both complete manifests only via separately reviewed/authorized historical source evidence; validate exact authenticated baseline source/run/attempt/object hashes, and then pass **copies** to this pure diagnostic. No unreviewed R2 request or refetch of the full Core100 training dataset is necessary for the field comparison. If auth/manifest bytes remain inaccessible, status stays `RUNTIME_CHANGED / REVIEW_REQUIRED` with narrow Runner-version evidence, not a guessed repair. Any Python/runner/dependency pin, rebaseline, retrain or promotion requires separate scope, approved versioned contract and new acceptance gates.

Related-work reconciliation — 2026-10-26: #810 and V3 successor #812 have merged; protected-main Pages run [40332377066](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40332377066) passed build, deploy and 66 desktop/mobile checks. Shadow feature successor #814 merged at `a9518b0a1d93f0b47304715a2e4b5a6ec0e9a9ce`; #809 is closed unmerged with source retained. Earlier #807 remains unmerged. These delivery results do not clear runtime drift, qualify the REJECT model or establish a formal PAPER run. Original dated runtime observations above retain their scope; this appendix does not claim full manifest authentication.
