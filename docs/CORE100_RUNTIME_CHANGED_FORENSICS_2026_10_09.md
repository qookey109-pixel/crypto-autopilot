# Core100 V0.2 scheduled comparison: `RUNTIME_CHANGED` forensics

**Reviewed:** 2026-10-09 Asia/Taipei. **Authority:** read-only diagnosis from existing GitHub logs and merged frozen comparator. **No new execution authority.** This note does not declare the Health alert recovered.

## Exact source observations

| Dimension | Authorized one-time baseline | Subsequent natural scheduled comparison |
| --- | --- | --- |
| GitHub run | [36110721415](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415), 2026-09-25 | [37196295102](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37196295102), 2026-10-04 |
| Workflow result | success | failure: `REVIEW_REQUIRED / RUNTIME_CHANGED` |
| Runner OS | ubuntu-24.04 | ubuntu-24.04 |
| Runner image header version | `20260920.314.1` | `20260927.320.1` |
| Requested / installed Python | 3.13 / CPython `3.13.15` | 3.13 / CPython `3.13.15` |
| Explicit `setuptools` | `80.9.0` | `80.9.0` |
| Recorded main dependencies | `boto3=1.43.75`, `botocore=1.43.75`, `pyarrow=21.0.0`, project `0.1.0` | Same versions in pip install log |
| Dataset fingerprint | `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876` | Same |
| Runtime guard fingerprint | `c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79` | Same |
| Experiment fingerprint | `12ff384302785645144832115114a88f726bcc4ce51caa56497bec1209c76ed7` | `6e014580e0b85135fc9f44b556e7773a81c200b29ad7dc3aa9555901b300fba6` |
| Training performed on that run | Yes: consumed authorized baseline | No |
| R2 writes on that run | Authorized baseline outputs | None |
| Holdout access | False | False |

The baseline records `model_quality_gate.status=REJECT`, despite its successful training execution. The failed weekly comparator must not be interpreted as model training, model promotion, or newer accepted model evidence.

## Why the image version is material

The merged `src/crypto_autopilot/training/fingerprint_collector_v0_2.py` explicitly records GitHub Actions environment variables `ImageOS` and `ImageVersion` as `runtime_manifest.runner_image`. `fingerprint_v0_2_execution.compare_fingerprints` checks exact `runtime_manifest` equality **before** checking `dataset_fingerprint` and `experiment_fingerprint`, and returns `REVIEW_REQUIRED / RUNTIME_CHANGED` when it differs. `experiment_fingerprint` also includes the complete normalized runtime manifest.

The logs independently show the runner-image header changed between these executions. **This is a sufficient identified cause candidate for the comparator's `RUNTIME_CHANGED` result**, conditional on GitHub's recorded `ImageVersion` agreeing with the visible runner image header. The precise changed field(s) of the stored runtime manifests have **not** been independently diffed: the logs do not expose full manifests, and other OS, kernel, tooling or distribution metadata could also have changed. Do not claim the runner image was the *only* difference.

## Permitted next step

1. Keep the original baseline, existing R2 latest pointer, `REVIEW_REQUIRED` result and current frozen fingerprints unchanged.
2. Read-only compare **the two already stored runtime manifests** from existing authorized evidence if a compliant bounded mechanism becomes available; record exact changed keys and source IDs without public secrets or rewriting evidence.
3. Independently review a **new versioned runtime-change policy** if scheduled comparisons are intended to tolerate expected hosted-image rotations. Document tradeoffs and seek separate authorization. **Do not** silently ignore `runner_image`, reset the reference fingerprint, grant retraining, or enable promotion.
4. Health → Maintenance remains an open observation, not `RECOVERED`; wait for a separately verified qualifying natural success.

**Safety:** CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER; zero paid calls; no new training, holdout, provider, source-switch, R2 write, D1, paper order, or real-money authority.
