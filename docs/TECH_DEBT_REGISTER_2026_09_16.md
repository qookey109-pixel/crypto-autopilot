# Technical Debt Register — 2026-09-16

Repository `main` is authority. This register tracks cleanup work; it does not grant execution, trading, provider, holdout, promotion, or deployment authority.

## P0 — current-truth convergence

### TD-001 — Multiple present-tense status authorities

Status: **IN PROGRESS**

Problem:

- `README.md`, `PROJECT_STATUS.md`, status JSON, Dashboard projections, and security/governance prose can describe different lifecycle states.
- Older September 13 text still reports Core100 `8/10` and Training `SKIPPED` even though History is complete and Training run `34918219864` completed successfully.

Target:

- `CURRENT_STATUS.md` is the concise human entrypoint.
- `research/status/current-operations-v0-2.json` is the machine-readable current-state companion.
- Other documents are projections or historical evidence, never independent current truth.

Exit criteria:

- CI verifies the current entrypoint and machine-readable companion agree on reviewed main, lifecycle, run IDs, and closed authority boundaries.
- README / PROJECT_STATUS / Dashboard clearly reference the current entrypoint rather than restating stale present-tense status.

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

Status: **OPEN**

Problem:

- Dashboard workflows and fixtures still contain older V0.12 / historical state assumptions.
- Training completion and current Pionex validation state are not consistently projected.

Target:

- Generate Dashboard current state from the machine-readable current-operations snapshot plus immutable evidence.
- Keep Dashboard a projection, never authority.

### TD-004 — Security/current-runtime prose drift

Status: **OPEN**

Problem:

- `SECURITY.md` security boundaries are sound, but some present-tense workflow wording still describes V0.12 as the current scheduled path after its bounded window.

Target:

- Preserve secret/runtime/holdout rules.
- Rewrite only stale present-tense operational wording as historical/superseded state.

### TD-005 — Open PR backlog crosses architecture generations

Status: **OPEN**

Current known lanes include active/recent work (#302, #305, #306, #307, #315) and legacy salvage drafts (#166, #167, #168, #199, #249).

Target:

For each open PR classify against current main as one of:

- ACTIVE_CURRENT;
- REBUILD_FROM_CURRENT_MAIN;
- PRESERVE_SALVAGE_DRAFT;
- SUPERSEDED_BY_MAIN;
- CLOSE_AFTER_PRESERVATION_PROOF.

Do not merge an old branch merely because its historical CI was green.

## P2 — workflow and quality maintenance

### TD-006 — Hard-coded scheduled-workflow count

Status: **OPEN**

Problem:

- Research Automation Health V0.2 asserts an exact scheduled workflow count of `7`.
- Adding or retiring a scheduler requires synchronized code/config changes and can create avoidable drift.

Target:

- Introduce an explicit active-workflow registry.
- Health checks derive expected scheduled workflows from that registry and still fail closed on omissions.

### TD-007 — Quality visibility is narrower than project size

Status: **OPEN**

Current blocking CI intentionally limits Ruff to core correctness classes and does not run a type checker.

Target:

- Add non-blocking reports first for broader lint/type/complexity/dead-code visibility.
- Do not immediately expand required gates and destabilize protected main.

### TD-008 — Dependency/security maintenance visibility

Status: **OPEN**

Target:

- Add review-only dependency-update visibility; no auto-merge.
- Evaluate CodeQL or equivalent non-blocking static security analysis before making it required.

## P3 — code structure

### TD-009 — Large responsibility concentration in training modules

Status: **DEFERRED**

Observation:

- `training/quality.py` is large enough to merit responsibility review.

Target:

- First add characterization tests around current behavior.
- Split responsibilities only after control-plane and Pionex validation work are stable.
- No behavior-changing rewrite solely for file size.

## Explicit non-goals

Technical-debt cleanup must not silently:

- open the replacement holdout;
- switch Binance/Pionex provenance;
- mutate frozen receipts or evidence;
- relax model-quality gates;
- change strategy thresholds;
- authorize promotion, formal trade plans, real-money orders, or live trading;
- provision new paid services or credentials.
