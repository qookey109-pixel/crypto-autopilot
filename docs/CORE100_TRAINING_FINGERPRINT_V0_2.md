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

V0.1 remains the active scheduled workflow. The V0.2 config and receipt are preparation evidence only. A separate versioned cutover authority and an implementation review are required before changing the scheduled runner. The original V0.1 config, receipt, baseline, workflow and user checkout remain untouched.
