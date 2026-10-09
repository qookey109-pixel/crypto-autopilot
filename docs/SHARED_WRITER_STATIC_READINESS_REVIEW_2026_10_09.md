# Four R2 writer routes — static shared-admission review (2026-10-09)

Authority boundary: **CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / FREE-ONLY / 0 USD**. This is a CI read-only *repository-source* review, not account-wide discovery, execution, D1 provisioning, R2 integration, training, model promotion, Cloud Paper activation or real trading.

## Motivation

The shared writer registry correctly lists four currently effective R2-capable workflow entrypoints but their `registration_state` values remain `DECLARED_SHARED_ADMISSION_NOT_VERIFIED`. V0.4 separately includes a SQL/SQLite reservation design and an `AdmissionQueryMeter` interface. None of this proves that these four entrypoints actually reserve from a common durable account-wide D1 ledger **before external access**. Merely flipping a registry status or relying on a simulated local meter must never confer production access.

## Reviewed current source routes

| Writer | Workflow | Script / direct R2 evidence | Shared admission |
| --- | --- | --- | --- |
| Research Signal Layer V0.2 | `.github/workflows/research-signal-layer-v0-2.yml` | `scripts/run_research_signal_layer_v0_2.py`; `--publish-r2`, direct `R2Store` construction and its own R2 headroom check | **UNVERIFIED** |
| Core100 training V0.2 | `.github/workflows/binance-usdm-detailed-training-v0-1.yml` | `scripts/train_binance_detailed_history_models_v0_4.py`; R2-backed training data path; the existing weekly comparator is currently fail-closed with `RUNTIME_CHANGED` | **UNVERIFIED** |
| Live Paper coordinator | `.github/workflows/live-paper-run-coordinator-v0-1.yml` | `scripts/run_live_paper_coordinator_v0_1.py`; dispatch-only `--store-backend r2`, direct `R2Store` | **UNVERIFIED** |
| Live Paper recovery | `.github/workflows/live-paper-run-recovery-v0-1.yml` | `scripts/reconcile_live_paper_run_v0_1.py`; dispatch-only `--store-backend r2`, direct `R2Store` | **UNVERIFIED** |

These are **traceable existing source paths**, not a declaration that each was recently run or wrote anything to Cloudflare. The old one-time Core100 bootstrap is consumed; no restart, rebaseline, bootstrap or model-quality inference follows from the static analysis. The live Paper production loop remains `NOT_WIRED / NOT_RUN / NOT_CONFIGURED`.

## Safeguard in this PR

`scripts/inspect_shared_writer_static_readiness_v0_1.py` reads only the four named workflow/script sources and the existing registry from a GitHub CI checkout. It fails the synthetic test on route, R2 marker, identity, writer-count or entrypoint shape drift; it also refuses fabricated `SHARED_ADMISSION_VERIFIED`, `d1_provisioned`, `activation_enabled` and `account_wide_coverage_proven` claims under this **reviewed v0.1 source shape**. Any legitimate future wiring needs a separately reviewed successor with actual runtime proof, rather than adding a textual claim.

Its result **always** remains `REVIEW_REQUIRED_SHARED_ADMISSION_UNVERIFIED`; it does not call Cloudflare and cannot inspect all transitive code paths or other account services. Evidence of a keyword in a source file is *not* durable atomic query metering proof. Running this validator (via pytest) protects a current frozen review baseline and is **not** proof of the absence of every potential R2 read/write. Registered current external R2 writers were scoped in an older owner statement, but future writers and D1 or other-project usage remain incomplete.

## Still necessary before any Cloud Paper runtime

A separately authorized writer-by-writer integration with `SharedWriterR2Budget`/V0.4 and a durable prepaid query controller; D1 provisioning under explicit authority; exact Cloudflare rows-read/rows-written/storage and concurrency calibration; fresh *account-wide* R2/D1 usage and zero-cost headroom; full external/new writer owner attestation; tests covering crash, retries and degraded transports; model-quality and market-context qualification; and controlled formal Paper and natural schedule evidence.

**This is a blocking safety review, not an implementation of shared-account admission.** Nothing here permits real-money orders, paid services, source switching, training or holdout access.
