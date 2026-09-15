# Technical Debt Register — 2026-09-16

Repository `main` is authority. This register tracks cleanup work; it does not grant execution, trading, provider, holdout, promotion, or deployment authority.

## P0 — current-truth convergence

### TD-001 — Multiple present-tense status authorities

Status: **IN PROGRESS — CORE CONVERGENCE IMPLEMENTED ON PR #322**

Problem:

- `README.md`, `PROJECT_STATUS.md`, status JSON, Dashboard projections, and security/governance prose can describe different lifecycle states.
- Older September 13 text still reports Core100 `8/10` and Training `SKIPPED` even though History is complete and Training run `34918219864` completed successfully.

Implemented on PR #322:

- `CURRENT_STATUS.md` is the concise human entrypoint.
- `research/status/current-operations-v0-2.json` is the machine-readable current-state companion.
- `AGENTS.md` reads current operations before dated status files.
- root `README.md` and `PROJECT_STATUS.md` now project current lifecycle state while preserving required historical compatibility markers.
- regression tests prevent `8/10 / Training SKIPPED` from returning as current state.

Remaining exit criterion:

- finish wiring the same machine-readable state into the production Dashboard projection and obtain exact-head green CI.

### TD-002 — Pionex current-main evidence gap

Status: **OPEN / OPERATIONAL**

Problem:

- PR #321 is merged on current main and fixes narrow bounds-only invalid-candle boundary handling.
- Previous materialization run `34991627998` failed closed before that fix.
- No new materialization result from `main=f5cf7429...` has yet been frozen as current-main execution evidence.

Target:

- Manually dispatch `.github/workflows/pionex-validation-materialization-v0-1.yml` from current main.
- Verify the secret-free report and preserve only the allowed validation evidence.

Exit criteria:

- Current-main run ID, outcome, artifact digest, partition/coverage status, and authority assertions are recorded without opening holdout/training/source-switch/trading authority.

## P1 — control-plane projections

### TD-003 — Dashboard projection drift

Status: **IN PROGRESS — CURRENT OPERATIONS OVERLAY IMPLEMENTED**

Problem:

- Historical Dashboard overlay logic still contains V0.12-era current-state assumptions.
- Training completion and current Pionex validation state were not consistently projected.

Implemented on PR #322:

- added `scripts/apply_dashboard_current_operations_v0_2.py` as a final fail-closed current-state overlay after historical lineage projection;
- added tests for Core100 History/Training, model-quality REJECT, threshold replay no-change, Pionex pending current-main validation, V0.12 historical status, expired V0.12 execution flags, and closed holdout/source-switch/trading boundaries;
- ran a temporary non-deploying pull-request validation workflow against the full historical Dashboard build chain and obtained SUCCESS; the temporary workflow was then removed so one-time validation did not become permanent control-plane inventory.

Remaining exit criterion:

- after exact-head validation passes, wire the current overlay into the real Dashboard authority snapshot / Pages build without deleting historical lineage checks.

### TD-004 — Security/current-runtime prose drift

Status: **IMPLEMENTED ON PR #322 / AWAITING EXACT-HEAD CI**

Implemented:

- preserved secret/runtime/holdout rules;
- changed V0.12 from false present-tense current scheduling language to its exact historical bounded window;
- documented the current Pionex validation workflow as manual-only and validation-scoped.

### TD-005 — Open PR backlog crosses architecture generations

Status: **TRIAGED / PRESERVATION REVIEW STILL OPEN**

Current classification is recorded in:

- `docs/OPEN_PR_TRIAGE_2026_09_16.md`
- `research/status/open-pr-triage-v0-2.json`

Current lanes:

- `ACTIVE_CURRENT`: #322
- `REBUILD_FROM_CURRENT_MAIN`: #315, #307, #306
- `SUPERSEDED_PENDING_PRESERVATION_PROOF`: #305
- `PRESERVE_DIAGNOSTIC_EVIDENCE`: #302
- `SALVAGE_DRAFT`: #249, #199, #168, #167, #166

Do not merge an old branch merely because its historical CI was green. Do not close #305 until unique useful content is proven preserved or intentionally superseded.

## P2 — workflow and quality maintenance

### TD-006 — Hard-coded scheduled-workflow count

Status: **IMPLEMENTED ON PR #322 / AWAITING EXACT-HEAD CI**

Previous problem:

- Research Automation Health V0.2 repeated an exact scheduled workflow count of `7` even though the core coverage engine already scans Repository schedules and detects missing/duplicate monitoring.

Implemented:

- config policy is now `EXACT_REPOSITORY_SCHEDULE_INVENTORY`;
- expected count is derived from `config["workflows"]` rather than a magic number;
- the workflow requires Repository scheduled count = monitored count = inventory count;
- unmonitored schedules, duplicate monitored entries, and manual-event masking remain fail-closed;
- a regression test prevents the literal `scheduled_workflow_count == 7` assertion from returning.

### TD-007 — Quality visibility is narrower than project size

Status: **OPEN**

Current blocking CI intentionally limits Ruff to core correctness classes and does not run a type checker.

Target:

- add non-blocking reports first for broader lint/type/complexity/dead-code visibility;
- do not immediately expand required gates and destabilize protected main.

### TD-008 — Dependency/security maintenance visibility

Status: **OPEN**

Target:

- add review-only dependency-update visibility; no auto-merge;
- evaluate CodeQL or equivalent non-blocking static security analysis before making it required.

## P3 — code structure

### TD-009 — Large responsibility concentration in training modules

Status: **DEFERRED**

Observation:

- `training/quality.py` is large enough to merit responsibility review.

Target:

- first add characterization tests around current behavior;
- split responsibilities only after control-plane and Pionex validation work are stable;
- no behavior-changing rewrite solely for file size.

## Explicit non-goals

Technical-debt cleanup must not silently:

- open the replacement holdout;
- switch Binance/Pionex provenance;
- mutate frozen receipts or evidence;
- relax model-quality gates;
- change strategy thresholds;
- authorize promotion, formal trade plans, real-money orders, or live trading;
- provision new paid services or credentials.
