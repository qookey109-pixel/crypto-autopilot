# Core100 Training Fingerprint V0.2 — Preparation Only

Prepared: 2026-09-23 19:09 UTC (2026-09-24 03:09 Asia/Taipei). Evidence source: repository main `766fc2a9b75a9c728901a72393734d68d5799a7d`.

**Status: PREPARED_NOT_ACTIVE.** This proposal does not change the scheduled V0.1 runner, activate a new fingerprint, authorize training, read R2, request provider data, or access holdout data. See the machine-readable [contract](../config/core100_training_fingerprint_v0_2.json) and [preparation receipt](../research/receipts/2026-09-24-core100-training-fingerprint-v0-2-prepared.json).

## Finding

The effective V0.1 fingerprint tracks 10 paths. All 10 current blobs still match its frozen baseline, but src/crypto_autopilot/**features/advanced.py** is not among them and its blob differs from the source used by the legacy training run. A synthetic regression changed that omitted feature blob while preserving all 10 tracked blob values; V0.1 returned the same baseline experiment identity and did not even request the omitted path. Changing a tracked trainer blob or the dataset hash changes the identity.

Therefore, **if** the current dataset fingerprint and latest pointer still equal the legacy baseline, V0.1 can return NO_CHANGE even though one model feature implementation has changed since training. This audit did not read production R2, so it does not assert the current dataset fingerprint or latest pointer.

## Import and behavior classification

The full static source closure contains **31 Python files** after resolving absolute and relative local imports, Python package initializers, and the two explicit Python file-loader runner edges. The old local proposal's 18-file list omitted **backtest.py** and **risk.py**; the complete closure adds those two plus 11 package-initialization imports.

The prepared contract splits the closure:

- **14 result-identity files:** the original runner, the V0.2 quality/example wrapper, and code that affects accepted historical rows, decoded candles, features, labels or fitted model output. Supporting identity paths are the training config, requirements/ci-constraints.txt and pyproject.toml.
- **17 runtime import-guard files:** modules loaded by the runner but with no observed Core100 result call site. Changes require REVIEW_REQUIRED, without automatic retraining. backtest.py and risk.py are imported through the FundingPoint type in binance_historical.py; the Core100 training path uses its interval mapping and does not call their backtest or sizing functions. exchanges/__init__.py also imports paper and Pionex modules that the Core100 path does not instantiate.

Unknown dynamic imports or missing runtime data fail closed. A NO_CHANGE result would require the same dataset, result identity, exact runtime/dependency manifest and runtime guard.

## Legacy baseline migration

The legacy GitHub source commit is dc10ce590c8731fbef21115e0e3d3423cbcc7cf1. Direct GitHub blob metadata shows that among the 14 proposed result-identity files, **13 match and one differs**: features/advanced.py. The V0.3 dedupe wrapper was absent from that commit. The three supporting config/dependency files match; the training workflow changed. The old fingerprint config records Python **3.13**, but not the exact patch version or the installed-distribution manifest now required for reproducible identity.

The V0.1 pointer is therefore REVIEW_REQUIRED: it cannot be migrated or reused automatically under V0.2. Missing migration evidence must not trigger training or an R2 write.

## Runtime contract proposed for V0.2

Record the Python implementation and full version, cache tag, platform/architecture/libc, and normalized, sorted installed distribution names and versions from an isolated project environment, including pip and build-backend/install-tool versions. Record the GitHub runner image metadata when available. Hash canonical UTF-8 JSON with sorted keys. Keep the dataset fingerprint bound to the catalog SHA and ordered shard-receipt SHA values.

If only a runtime import-guard file changes, return REVIEW_REQUIRED; do not retrain automatically. Hash the guard using canonical JSON over path/blob rows sorted by path. Workflow or authority-receipt changes also require review. If any required runtime or dependency field is unavailable, return REVIEW_REQUIRED. Exact unchanged inputs may return NO_CHANGE with no training and no R2 write, but only after a separately reviewed authority activates a runner implementing this contract.

## Current state and next action

V0.1 remains the active scheduled workflow. The V0.2 config and receipt are preparation evidence only. The pure comparison implementation below is available for synthetic review. A separate versioned cutover authority and an implementation review are required before changing the scheduled runner. The original V0.1 config, receipt, baseline and workflow remain untouched.

## Pure implementation checkpoint — 2026-09-24

The new [fingerprint module](../src/crypto_autopilot/training/fingerprint_v0_2.py) implements the prepared comparison without importing a runner, storage client or provider module. It accepts in-memory inputs only and has no file reads, environment collection, network requests, training or write callback. Its three entrypoints are:

- `normalize_runtime_manifest(raw)`: validate and copy caller-supplied runtime evidence.
- `build_fingerprint(contract_bytes=..., dataset_fingerprint=..., git_blobs=..., runtime_manifest=...)`: validate all 36 blob entries, then hash the result identity and runtime guard separately. Invalid inputs raise `FingerprintValidationError`.
- `compare_prepared_fingerprints(contract_bytes=..., current=..., previous=...)`: rebuild both records and compare them. Missing, malformed, legacy or changed evidence returns `REVIEW_REQUIRED`. An exact match returns a prospective `NO_CHANGE` with `mode=PREPARATION_ONLY` and `execution_authorized=false`.

The module pins the frozen contract's exact SHA-256, `2ee82c6d030c3ebdb49b985220f07a7e7c1109f4fef7c15b27fba0ae02922d2a`. It rejects a shortened inventory or modified authority flags rather than accepting a caller-edited contract. The frozen config and preparation receipt have not been rewritten.

### Runtime evidence shape

All fields are required; unknown fields and incomplete inventories are rejected:

| Fields | Accepted representation |
| --- | --- |
| `implementation`, `version`, `cache_tag`, `platform`, `system`, `release`, `machine` | Nonempty strings; `version` starts with a full Python major.minor.patch version. |
| `libc` | Two nonempty strings, `[name, version]`, for the governed Linux runtime. |
| `distributions` | Complete isolated-environment list of `{name, version}`; names normalized to lowercase with `-`, `_` and `.` runs collapsed to `-`, then sorted; duplicate normalized names rejected. Must include pip and the project package. |
| `install_tools` | Complete list of `{name, version}`, including pip and setuptools; versions agree with installed distributions when present. An isolated build backend may be absent from the runtime distribution list. |
| `project_version` | Exact match for the `qookey-crypto-autopilot` distribution. |
| `runner_image` | `{os, version}` with nonempty strings, or explicit `null` when unavailable. |
| `isolated_environment`, `distribution_inventory_complete`, `install_tools_complete` | Boolean `true` caller attestations; integers and strings are rejected. |

Caller attestations and SHA strings do not authenticate production evidence. A future collector must prove the dataset digest binds the catalog and ordered shard receipts, and collect the complete runtime/install-tool inventory from the actual isolated environment. This preparation module performs neither task.

### Decisions and migration

Workflow and authority-receipt blobs are checked against the frozen preparation anchors before reuse comparison, including when both records contain the same changed context. Changes to any result/support path, guard path, runtime or dataset require review. Stored digests are recomputed; they are never accepted alone.

The active V0.1 runner already writes a latest pointer whose schema ends in `v0.2` (`binance-usdm-intraday-research-training-latest-v0.2`). That label is not V0.2 fingerprint provenance. Such a pointer is rejected by this module; only complete `qookey-core100-training-prepared-evidence-v0.2` records can be compared. No mismatch or missing legacy record triggers training.

### Verification and next delivery

[Behavior tests](../tests/test_core100_training_fingerprint_v0_2.py) exercise every result/support/guard/context path, runtime normalization and missing evidence, tampered records, legacy pointers, and a fresh Python `-S` subprocess with selected file/network/subprocess APIs and production imports blocked. This is a bounded side-effect regression check, not a comprehensive I/O sandbox. Run the relevant regression suite with Python 3.11 or newer:

```sh
PYTHONPATH=src python -m pytest tests/test_core100_training_fingerprint_v0_1.py tests/test_core100_training_fingerprint_v0_2_prepared.py tests/test_core100_training_fingerprint_v0_2.py -q
ruff check src/crypto_autopilot/training/fingerprint_v0_2.py tests/test_core100_training_fingerprint_v0_2.py
```

On 2026-09-24, the isolated implementation based on main `f9296aca33858c907b42e825db8a9d334df1986e` passed these three pytest files with Python 3.13.15: **25 tests and 139 subtests**. The full-repository `ruff check src tests scripts` and `git diff --check` also passed. These are synthetic implementation/regression results, not production execution or deployment evidence.

Next prepare a **new versioned cutover proposal** covering authenticated runtime collection, legacy-baseline disposition and the exact runner integration. Importing this new module into the active runner will change the import closure: the new module and any collector must be inventoried under that successor authority. Do not silently reuse or edit the frozen 31-file preparation inventory. A merged implementation alone does not activate the comparator, certify a production `NO_CHANGE`, authorize retraining, or change model quality from REJECT.
