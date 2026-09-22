# Technical Debt Register — 2026-09-17 (refreshed 2026-09-22)

Repository `main` is authority and must be resolved live at read time. Evidence basis for this refresh: `09dfb0d79b88dc56f3cb582c91d8091617437ce2` after PR #426 merged. This SHA is historical review context, not a latest-main claim.

This register tracks cleanup work only. It grants no execution, provider, R2, holdout, promotion, source-switch, deployment, trading, or merge authority.

## P0 — current-truth convergence

### TD-001 — Multiple present-tense status authorities

Status: **COMPLETE**

Completed through PRs #322, #323, and #339:

- `CURRENT_STATUS.md` is the concise current-operations entrypoint;
- machine-readable Current Operations V0.3 exists;
- repository `main` is resolved live at read time;
- dashboard/homepage current projection is applied after historical projection;
- stale `8/10`, Training `SKIPPED`, and V0.12-active wording is guarded against reappearing as current state.

### TD-002 — Pionex repository-current evidence gap

Status: **COMPLETE FOR THE V0.2 MATERIALIZATION CONTRACT**

Resolved by the governed V0.2 materialization result and merged evidence/convergence work:

- materialization run `35054729471`: PASS;
- 197 selected markets;
- 682 partitions;
- 1,534 provider requests;
- immutable completion evidence preserved by PR #337;
- current-status/dashboard convergence completed by PR #339.

This does **not** claim complete 197-market multiyear history and does **not** claim Core100 Pionex training was performed.

## P1 — control-plane projections and backlog

### TD-003 — Dashboard / homepage projection drift

Status: **COMPLETE**

PR #323 fixed projection ordering and stale homepage restoration. PR #339 then converged the same surfaces on Pionex V0.2 COMPLETE/PASS.

### TD-004 — Security/current-runtime prose drift

Status: **COMPLETE VIA PR #322**

Historical V0.12 wording remains historical; current runtime and safety boundaries remain closed and explicit.

### TD-005 — Open PR backlog crosses architecture generations

Status: **ACTIVE / REFRESHED 2026-09-22**

Current classification is recorded in:

- `docs/OPEN_PR_TRIAGE_2026_09_22.md`;
- `research/status/open-pr-triage-v0-5.json`.

Current live backlog:

- six Dependabot PRs only: #326–#331;
- #302, #306, #307, #315, #336 and the older salvage drafts are closed historical references;
- old architecture branches are no longer represented as active merge lanes;
- each dependency PR still requires current-main compatibility review and its own merge authorization.

The V0.5 review order separates patch-level tooling/SDK updates from major GitHub Action/runtime changes and records the current-main contract conflicts for #330/#331.

No PR is closed or merged merely by this classification.

## P2 — workflow and quality maintenance

### TD-006 — Hard-coded scheduled-workflow count

Status: **COMPLETE**

Research Automation Health derives the expected schedule count from repository inventory and fails closed on mismatches. The repaired contract has also passed on current-main scheduled execution.

### TD-007 — Quality visibility is narrower than project size

Status: **PARTIAL / BASELINE VISIBILITY EXPANDED**

Already implemented:

- blocking Ruff remains limited to core correctness classes;
- CI on Python 3.13 emits non-blocking quality visibility;
- `scripts/quality_visibility.py` reports Python inventory, syntax issues, TODO/FIXME/HACK markers, annotation coverage, broad Ruff diagnostics, largest/decision-heavy definitions, and heuristic private dead-code candidates;
- `scripts/type_visibility.py` emits a separate non-blocking mypy semantic baseline for `src/crypto_autopilot`;
- mypy `2.3.1` is pinned directly in the informational CI step so the frozen V0.10 dependency snapshot remains unchanged; diagnostics are uploaded as `type-visibility.json`;
- no lint/type threshold is enforced by these informational reports.

Still missing:

- review of measured baseline noise before any signal is considered for promotion to a required gate;
- dedicated semantic dead-code tooling beyond the current conservative heuristic.

Do not make these blocking until baseline noise is measured and reviewed.

### TD-008 — Dependency/security maintenance visibility

Status: **PARTIAL / SECURITY AND DEPENDENCY TRIAGE CURRENT**

Already implemented:

- `.github/dependabot.yml` tracks both `pip` and GitHub Actions monthly;
- update PRs are review-only; no auto-merge authority is introduced;
- repository-controlled CodeQL runs as non-blocking security visibility and has passed on current main;
- Open PR Triage V0.5 records a current dependency review order and separates patch-level updates from major action/runtime changes;
- dependency classifications remain review guidance only and do not grant merge authority.

Still missing:

- actual current-main rebuild/compatibility decisions for the six open dependency PRs.

## P3 — code structure

### TD-009 — Large responsibility concentration in training modules

Status: **DEFERRED**

`training/quality.py` remains a responsibility-splitting candidate. First add characterization tests around current behavior; do not perform a behavior-changing rewrite solely for file size.

## Current cleanup order

1. Keep this refreshed PR triage aligned with live `main`; do not merge stale architecture-generation branches directly.
2. Review dependency PRs as a separate lane; breaking-major upgrades require explicit compatibility review and their own merge authorization.
3. Review quality/type/security baseline evidence before considering any new required gate.
4. Treat #302/#315/#306/#307 and #166/#167/#168/#199/#249 as closed historical salvage only; rebuild selected ideas from current `main` only if deliberately revived.
5. Review the 261-error mypy baseline by category before considering any type gate.
6. Leave large-module responsibility splitting deferred until characterization coverage justifies it.

## Explicit non-goals

Technical-debt cleanup must not silently:

- open the replacement holdout;
- authorize retraining or change the configured threshold;
- switch Binance/Pionex provenance;
- mutate frozen receipts or evidence;
- relax model-quality gates;
- authorize promotion, formal trade plans, real-money orders, or live trading;
- provision new paid services or credentials;
- merge or close another PR without its own reviewed decision.
