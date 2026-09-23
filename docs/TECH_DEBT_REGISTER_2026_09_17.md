# Technical Debt Register — 2026-09-17 (checkpoint refresh 2026-09-23)

Repository `main` is authority and must be resolved live at read time. Previous refresh evidence: `09dfb0d79b88dc56f3cb582c91d8091617437ce2` after PR #426. September 23 checkpoint evidence: `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51` after PR #478. Both are historical review context, not latest-main claims.

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

Status: **DEPENDENCY BATCH CLOSED / LIVE TRIAGE REQUIRED**

The September 22 [V0.7 review](OPEN_PR_TRIAGE_2026_09_22.md) records the completed #326–#331 dependency review: compatible replacements #447/#448 merged; incompatible/freeze-crossing proposals closed. The earlier six-open-PR list is historical.

At the September 23 refresh, #478 was already merged and #477 then merged as main `19968403407d932fab58aca9ec354e2ffd82b825`. Use live GitHub state plus exact current head/base/checks for new review. Closed architecture branches #302/#306/#307/#315/#336 remain historical salvage only. Follow the work order in `CURRENT_STATUS.md`.

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

- the original 261 errors across 49 files remain historical baseline evidence; use current CI visibility for the next non-execution narrowing slice;
- dedicated semantic dead-code tooling beyond the current conservative heuristic.

Do not make these blocking until baseline noise is measured and reviewed.

### TD-008 — Dependency/security maintenance visibility

Status: **PARTIAL / SECURITY AND DEPENDENCY TRIAGE CURRENT**

Already implemented:

- `.github/dependabot.yml` tracks both `pip` and GitHub Actions monthly;
- update PRs are review-only; no auto-merge authority is introduced;
- repository-controlled CodeQL runs as non-blocking security visibility and has passed on current main;
- Open PR Triage V0.7 records the completed dependency review; future proposals still require compatibility review;
- dependency classifications remain review guidance only and do not grant merge authority.

Still missing:

- ongoing review of future dependency proposals; the prior six-PR batch is complete under V0.7. No current open dependency backlog is inferred from the historical V0.5 record.

## P3 — code structure

### TD-009 — Large responsibility concentration in training modules

Status: **DEFERRED**

`training/quality.py` remains a responsibility-splitting candidate. First add characterization tests around current behavior; do not perform a behavior-changing rewrite solely for file size.

## Current cleanup order

Follow the dated checkpoint in `CURRENT_STATUS.md` and the [continuation runbook](PROJECT_CONTINUATION_RUNBOOK.md). These IDs extend this existing register; they add no execution authority. External waiting does not prevent independent eligible work.

| ID / priority | Checkpoint status | Next action | Completion evidence / boundary |
| --- | --- | --- | --- |
| TD-010 / P0 — Pages and Health | PARTIAL — PAGES VERIFIED / HEALTH WAITING | Read the first natural Health schedule created after Pages run `35843351924` | Pages `35843351924` build/deploy/browser all SUCCESS on main `87ad32f...`; require a later natural Health result, with no dispatch or substitute event |
| TD-011 / P1 — Local reconciliation | DISPOSITION_REVIEWED, integration pending | Read local inventory and reconciliation plan indexed in the runbook; recheck main before each salvage slice | 78 paths mapped, original hashes unchanged; review candidate tests at current source paths; no removal/reset/overwrite from inventory alone |
| TD-012 / P1 — Training fingerprint | LOCAL_PROPOSAL, not activated | Review full model-affecting dependency closure, baseline migration and synthetic regression | Feature/dataset change changes identity; unchanged retains NO_CHANGE; no production training/R2 or frozen receipt edits |
| TD-013 / P1 — Delivery and PR review | PARTIAL — #477 MERGED / #479 DRAFT | Keep #479 separate and recheck its exact head/base/checks before any merge decision | #477 merged as `1996840...`; #479 still requires its own explicit merge decision; never reopen completed work from old counts |
| TD-014 / P2 — Removed registrations | BLOCKED_PERMISSION, 0/25 disabled | After Actions:write becomes available, revalidate exact removed-file list in [Actions map](GITHUB_ACTIONS_OPERATING_MAP.md) | User authorized these 25 only; read back state, preserve runs, exclude current/frozen-source workflows and Dependabot; no repeated 403 attempts |

After these items, continue TD-007 non-execution type narrowing from fresh CI visibility; keep type/security informational. TD-009 responsibility splitting stays deferred until characterization coverage justifies it.

The prior 261-error baseline and dependency-batch review are historical evidence, not current measurements or unfinished dependency work.

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
