# Core100 Training Fingerprint V0.2 Cutover Proposal V0.1

Status: PROPOSED_NOT_AUTHORIZED  
Prepared: 2026-09-25 03:16:11 UTC  
Repository: qookey109-pixel/crypto-autopilot  
Evidence basis: main e1d037d570e8641442448fad50422ca6f217b8aa

## Purpose and boundary

This document proposes how a future, separately authorized change could replace the active Core100 training fingerprint V0.1 with the prepared V0.2 contract. It is a review proposal, not an execution authority, and does not modify the active runner, workflow, fingerprint configuration, or frozen preparation receipt.

All preparation and any later implementation must remain CLOUD_ONLY. LOCAL_FILES_EXCLUDED_BY_USER. Any later collector or runner may execute only on a GitHub-hosted runner within a separately approved scope. The project budget remains 0 USD/month and PAPER / LIVE-PAPER ONLY.

## Evidence checked for this proposal

At the exact evidence-basis main above, the prepared V0.2 inventory still matches the repository:

- 31 Python files in the prepared static import closure;
- 3 result-identity support files;
- 2 execution-context anchors: the existing training workflow and its authority receipt;
- 36 of 36 Git blob IDs match the preparation receipt.

This is a metadata comparison only. No production latest pointer, R2 object, dataset object, provider, or holdout was read. The observation becomes historical if main advances.

The active V0.1 contract hashes 10 model-affecting paths and omits features/advanced.py. The prepared receipt records that this feature blob differs from the legacy training source. Therefore a V0.1 NO_CHANGE can be unsafe if the live dataset and old pointer still match the baseline. That production condition remains UNKNOWN because the pointer was not read.

The prepared V0.2 contract is PREPARED_NOT_ACTIVE. Its pure comparator is not imported by the active runner and receives caller-attested inputs; it does not collect authenticated runtime or dataset evidence.

## Proposed cutover decisions

1. Keep V0.1 as the only active scheduled implementation until a separate cutover authority and implementation are reviewed and merged.
2. Integrate into the existing weekly training workflow. Do not create a parallel workflow or cron.
3. Rebuild the import and execution-context inventory from the exact implementation PR head. The current 36-path snapshot is a baseline only: it does not include fingerprint_v0_2.py as an active import or any future collector module. Include each new module, package initializer, explicit file-loader edge, workflow, support file, and authority receipt required by the resulting execution path.
4. Preserve the V0.2 canonical identity and runtime rules in config/core100_training_fingerprint_v0_2.json. If its pinned contract or required paths change, prepare a successor contract and receipt; do not silently mutate the frozen preparation evidence.
5. Keep the existing provider, R2, training, model-quality, and PAPER/LIVE-PAPER boundaries. This proposal grants none of them.

## Evidence collection contract for a future authorized implementation

Before comparing fingerprints, a future GitHub-hosted collector must:

- Resolve the exact current main SHA and record the workflow run ID and attempt. Stop if checkout SHA, live main, source workflow, policy, or authority receipt does not agree.
- Recompute the exact source blob inventory from that main. Missing paths, unrecognized dynamic imports, incomplete pagination, changed execution-context anchors, or unknown runtime inputs return REVIEW_REQUIRED.
- Collect the full Python implementation and patch version, cache tag, platform, OS, release, architecture, libc, installed distribution name/version rows from an isolated project environment, pip and build/install tool versions, installed project version, and runner-image metadata when available. An incomplete inventory cannot support NO_CHANGE.
- Bind dataset identity to the catalog digest and ordered shard-receipt digests as specified by the prepared contract. Use only the data access already authorized by the future merged authority; do not expand object scope or fetch provider data for fingerprinting. Raw provider objects and holdout objects are outside this proposal.
- Store the resulting secret-free decision evidence in the existing GitHub Actions run summary or the already authorized training report. Do not create new external storage or increase retention without a separate cost review.

The collector must distinguish these outcomes:

| Evidence state | Required result |
| --- | --- |
| Exact dataset, result identity, runtime and runtime guard match with a valid V0.2 predecessor | NO_CHANGE; no training and no R2 write |
| V0.1 pointer, missing V0.2 predecessor, malformed or incomplete record | REVIEW_REQUIRED; no training and no R2 write |
| Runtime guard changed, runtime incomplete, or execution context changed | REVIEW_REQUIRED; no training and no R2 write |
| Dataset or result identity changed with otherwise complete evidence | Training may occur only if a separate merged authority explicitly permits it |
| GitHub/API, data, or permission evidence incomplete | UNKNOWN or BLOCKED; stop without fallback |

### Legacy baseline disposition

Do not convert, delete, overwrite, or automatically reuse the V0.1 latest pointer as a V0.2 predecessor. Keep its existing run and receipts as historical evidence. The prepared receipt says the legacy run lacks the exact Python patch and installed distribution inventory and that one result-identity source differs; migration is therefore REVIEW_REQUIRED.

The live pointer remains unread and UNKNOWN. The recommended cutover behavior is fixed: if only a V0.1 predecessor exists, or no valid V0.2 predecessor is available, return REVIEW_REQUIRED with no training and no R2 write. Do not auto-create the first V0.2 baseline. A one-time baseline creation/training operation requires a separate, exact versioned authority and receipt before execution. Until that authority exists and its evidence is reviewed, the V0.2 path remains blocked at this gate. This gives the proposal a deterministic safe default without treating a V0.1 record as V0.2 evidence.

## Implementation and acceptance gates

A later implementation PR must include:

1. An exact-head import-closure report covering the comparator, collector, runner and workflow, including dynamic imports and package initialization.
2. A source review proving V0.1 remains available only as historical evidence and that no old pointer can silently return NO_CHANGE under V0.2.
3. GitHub-hosted CI for the supported Python 3.12 and 3.13 matrix, plus synthetic cases for exact match, changed dataset, changed result source, runtime change, guard change, missing fields, malformed distributions, stale main, V0.1 pointer, and missing V0.2 predecessor. Both legacy/missing-predecessor cases must return REVIEW_REQUIRED without training, R2 writes, or automatic baseline creation.
4. Explicit assertions that REVIEW_REQUIRED and NO_CHANGE do not train or write to R2; unknown inputs fail closed; no automatic first-baseline creation occurs.
5. A versioned activation authority and receipt reviewed and merged before changing the active scheduled workflow. The authority must enumerate exact allowed R2 reads/writes, training behavior, FREE-ONLY headroom checks, and stop conditions.
6. Natural schedule evidence after activation. A PR check, push, manual run, workflow success, or synthetic fingerprint cannot prove a natural run, training result, or model-quality PASS.
7. A recovery plan before activation: on collector, migration, runtime, or publication failure, stop with REVIEW_REQUIRED and preserve the prior pointer. Do not automatically fall back to V0.1 deduplication, retrain, retry R2, or alter cadence. Recovery changes require an exact-main review and, when authority changes, a successor versioned authority.

## Proposed authority summary

This proposal permits review and documentation only. It does not authorize:

- active fingerprint cutover or changes to the weekly workflow;
- training, provider requests, R2 reads/writes, or pointer migration;
- holdout access, source switching, promotion, strategy/risk changes, or trading;
- dispatching, rerunning, or creating another schedule;
- local files, local runtime, paid services, or new long-lived secrets.

Next step: review this proposal, including its fail-closed baseline policy. If accepted, prepare the implementation and a separately versioned activation authority; this proposal authorizes neither cutover nor execution.