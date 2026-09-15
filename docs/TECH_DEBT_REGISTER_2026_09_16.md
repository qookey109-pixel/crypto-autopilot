# Technical Debt Register — 2026-09-16

Repository `main` is authority and must be resolved live at read time. This register tracks cleanup work; it does not grant execution, trading, provider, holdout, promotion, or deployment authority.

## P0 — current-truth convergence

### TD-001 — Multiple present-tense status authorities

Status: **CORE CONVERGENCE MERGED / SELF-REFERENCE FIX IN PR #323**

Merged by PR #322:

- `CURRENT_STATUS.md` as the concise human entrypoint;
- machine-readable Current Operations state;
- `AGENTS.md` current-first read order;
- root README / PROJECT_STATUS / SECURITY convergence;
- regression guards preventing old `8/10 / Training SKIPPED` text from becoming current state.

Follow-up defect discovered after merge:

- a status file cannot safely claim that its stored SHA is the latest future `main`, because the merge commit is created only after the file is merged.

Implemented on PR #323:

- Current Operations V0.3 uses `evidence_basis.parent_main_sha` with `is_latest_main_claim=false`;
- Repository `main` must be resolved live at read time;
- tests reject self-referential latest-main semantics.

Exit criterion:

- PR #323 exact-head CI and Dashboard validation green, then separate merge authorization.

### TD-002 — Pionex Repository-current evidence gap

Status: **OPEN / OPERATIONAL**

Problem:

- PR #321 merged the narrow bounds-only invalid-candle boundary fix.
- Previous materialization run `34991627998` failed closed before that fix.
- No new materialization result from the Repository's current live `main` has yet been frozen as post-fix validation evidence.

Target:

- manually dispatch `.github/workflows/pionex-validation-materialization-v0-1.yml` from live `main` after current control-plane work is stable;
- verify the secret-free report and preserve only the allowed validation evidence.

Exit criteria:

- Repository-current run ID, outcome, artifact digest, partition/coverage status, and authority assertions are recorded without opening holdout/training/source-switch/trading authority.

## P1 — control-plane projections

### TD-003 — Dashboard / homepage projection drift

Status: **IMPLEMENTED ON PR #323 / EXACT-HEAD VALIDATION IN PROGRESS**

Previous problem:

- historical Dashboard overlay still projected the expired V0.12 bounded window as present-tense active;
- production Pages did not apply the current-operations overlay;
- `build_delivery_overview.py` restored September 13 `8/10 / Training skipped / PR #292` text on every deployment;
- legacy `app.js` could overwrite the home history card with the dated progress snapshot.

Implemented on PR #323:

- Current Operations V0.3 final Dashboard overlay;
- production Pages and Zh-Hant authority workflows use `historical authority -> latest historical overlay -> Current Operations V0.3`;
- Core100 10/10, Training completed, Model Quality REJECT, threshold replay no-change and Pionex pending are asserted in production builds;
- V0.12 historical lineage remains preserved while expired present-tense execution/schedule flags are closed;
- homepage generator now treats dated simulation readiness as historical BTC sample evidence only;
- generated homepage current state comes from Current Operations V0.3;
- secret-free `data/current-operations.json` plus final `current-operations.js` prevents legacy app state from reintroducing dated present-tense values;
- build tests reject stale `8/10 分片`, `訓練尚未完成`, `PR #292`, and stale automation-health failure wording.

### TD-004 — Security/current-runtime prose drift

Status: **COMPLETE VIA PR #322**

- preserved secret/runtime/holdout rules;
- V0.12 wording now describes its exact historical bounded window rather than a current active schedule;
- current Pionex validation remains manual-only and validation-scoped.

### TD-005 — Open PR backlog crosses architecture generations

Status: **TRIAGED / REFRESHED FOR PR #323**

Current classification is recorded in:

- `docs/OPEN_PR_TRIAGE_2026_09_16.md`;
- `research/status/open-pr-triage-v0-3.json`.

Current lanes:

- `ACTIVE_CURRENT`: #323;
- recently merged control-plane batch: #322;
- `REBUILD_FROM_CURRENT_MAIN`: #315, #307, #306;
- `SUPERSEDED_PENDING_PRESERVATION_PROOF`: #305;
- `PRESERVE_DIAGNOSTIC_EVIDENCE`: #302;
- `SALVAGE_DRAFT`: #249, #199, #168, #167, #166.

Do not merge an old branch merely because its historical CI was green. Do not close #305 until unique useful content is proven preserved or intentionally superseded.

## P2 — workflow and quality maintenance

### TD-006 — Hard-coded scheduled-workflow count

Status: **COMPLETE VIA PR #322; DASHBOARD ASSERTIONS ALSO FIXED IN #323**

Implemented:

- Research Automation Health policy is `EXACT_REPOSITORY_SCHEDULE_INVENTORY`;
- expected count derives from `config["workflows"]` rather than magic number `7`;
- Repository scheduled count = monitored count = inventory count remains fail-closed;
- unmonitored schedules, duplicate monitoring, and manual-event masking remain fail-closed;
- production Dashboard assertions now also compare against inventory length instead of literal `7`.

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
