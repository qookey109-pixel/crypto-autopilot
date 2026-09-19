# Technical Debt Register — 2026-09-16

Repository `main` is authority and must be resolved live at read time. This register tracks cleanup work; it does not grant execution, trading, provider, holdout, promotion, or deployment authority.

## P0 — current-truth convergence

### TD-001 — Multiple present-tense status authorities

Status: **COMPLETE VIA PR #322/#323**

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

Exit result:

- PR #323 merged after exact-head CI and Dashboard validation; Current Operations V0.3 remains the fail-closed authority projection while live Repository `main` is resolved at read time.

### TD-002 — Pionex Repository-current evidence gap

Status: **COMPLETE / SUPERSEDED BY V0.2 MATERIALIZATION PASS**

Resolution:

- Pionex Validation Dataset Materialization V0.2 completed successfully on run `35054729471` from `main`;
- current status records stage `PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_2`;
- 197 selected markets and 682 partitions were materialized under the governed validation contract;
- completion evidence is preserved at `research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json`;
- incomplete provider-history states remain explicit; this is not a claim of complete 197-market multiyear history;
- no replacement-holdout access, Core100 Pionex training, source switch, model promotion, real-money order or real live-trading authority was opened.

The older V0.1 current-evidence gap no longer represents present-tense work.

## P1 — control-plane projections

### TD-003 — Dashboard / homepage projection drift

Status: **COMPLETE VIA PR #323**

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

Status: **COMPLETE / BACKLOG CONVERGED 2026-09-19**

Resolution:

- old architecture-generation drafts were compared against current `main` before closure;
- useful ZEC V0.2 evidence was preserved on current main without reviving one-shot execution authority;
- reusable Statistical Edge Gate V0.1 was salvaged separately from older Resource Hub/ZEC drafts;
- ZEC V0.3 design/provenance/status were preserved separately without data-access or experiment-execution authority;
- already-merged/current capabilities were not duplicated when closing paper-simulation, research-governance, technical-analysis, Pionex-role, REST/edge, Render-relay and integrated-promotion drafts;
- GitHub open pull-request count reached **0** before the 2026-09-19 Project Status convergence PR.

The historical triage files remain dated evidence. Future PRs must be evaluated against live `main`; historical green CI is not sufficient merge evidence after main advances.

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

Status: **NON-BLOCKING VISIBILITY EXPANDED / SEMANTIC TYPE CHECKER DEFERRED**

Current blocking CI intentionally remains unchanged.

Implemented informational visibility now includes:

- the existing size / AST / decision-point complexity inventory;
- TODO / FIXME / HACK marker counts;
- Python parameter / return annotation coverage without pretending this is semantic type checking;
- conservative heuristic dead-code candidates limited to unreferenced private module-level definitions;
- a broader non-blocking Ruff diagnostic view using `F,I,UP,B,C90`;
- artifact publication remains `continue-on-error: true` and enforces no thresholds.

A semantic type checker is still deferred to a later dependency-maintenance decision. These reports do not become promotion, validation, holdout, source-switch or trading gates.

### TD-008 — Dependency/security maintenance visibility

Status: **NON-BLOCKING VISIBILITY IMPLEMENTED / REQUIRED GATE NOT AUTHORIZED**

Dependency visibility:

- `.github/dependabot.yml` already performs monthly `pip` and `github-actions` update proposals;
- Dependabot remains review-only; this project config adds no auto-merge path.

Security visibility:

- `.github/workflows/security-visibility-codeql.yml` runs Python CodeQL on pull requests and pushes to `main`;
- the CodeQL v4 action is pinned to exact upstream commit `1c5b675653bb5c22dbe9b12b556ec555138e09fd`;
- there is intentionally no scheduled scan;
- analysis uses `upload: never` and publishes SARIF only as a 30-day GitHub Actions artifact;
- the job is `continue-on-error: true`, so security visibility is not a required promotion, merge, holdout, source-switch or trading gate.

Any future move to required CodeQL or Code Scanning upload needs a separate reviewed governance change.

## P3 — code structure

### TD-009 — Large responsibility concentration in training modules

Status: **CHARACTERIZATION BASELINE ADDED / REFACTOR DEFERRED**

Observation:

- `training/quality.py` remains large enough to merit responsibility review.

Characterization baseline now locks:

- exact V0.5 config/authority-pair validation output;
- canonical config-path loading and non-canonical fail-closed behavior;
- V0.3 bootstrap-baseline identity/count/authority invariants;
- validator input immutability for these governance surfaces;
- exact byte-level SHA-256 behavior.

The existing broader training-quality suite continues to cover dataset, model, weekly-review, R2-boundary and fail-closed behavior.

No responsibility split is performed by this step. Any future refactor must preserve these characterization tests and existing behavior; no rewrite is justified solely by file size.

## Explicit non-goals

Technical-debt cleanup must not silently:

- open the replacement holdout;
- switch Binance/Pionex provenance;
- mutate frozen receipts or evidence;
- relax model-quality gates;
- change strategy thresholds;
- authorize promotion, formal trade plans, real-money orders, or live trading;
- provision new paid services or credentials.
