# Technical Debt Register — 2026-09-17 (checkpoint refresh 2026-09-26)

Repository `main` is authority and must be resolved live at read time. Previous refresh evidence: `09dfb0d79b88dc56f3cb582c91d8091617437ce2` after PR #426. September 23 checkpoint evidence: `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51` after PR #478. September 24 signal-hardening checkpoint: `35c39d50957beccc634fd6346ef1554c20b32f35` after PR #492; all post-merge required checks passed and its delivery branch was removed. September 24 fingerprint-preparation checkpoint: PR #494 merged at `c06b46b61f6a26c7a8130cfd82b7c3408e29ed67`; post-merge tests, CodeQL, build, and Freeze Guard passed; Pages deploy and browser-production were skipped by path filters; the delivery branch was deleted. These SHAs are historical review context, not latest-main claims. September 25 convergence checkpoint: Core100 V0.2 baseline status was merged by PR #506 and the post-permission maintenance checkpoint by PR #507. September 26 current-truth checkpoint: Cloud Maintenance natural acceptance was closed by PR #509, the evidence/data organization index by PR #510, and dependency audit / CycloneDX SBOM visibility by PR #512; the reviewed main at this refresh is `25537c61b051d31002a576ec16bcb4a38aab9c31`. Resolve live main again before acting; this SHA is dated evidence.

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

- the original 261 errors across 49 files remain historical baseline evidence; current main CI now reports **65 mypy errors**;
- PR #519 made type visibility receipt-aware without changing blocking behavior: the 65 current errors are split into **3 receipt-bound** errors and **62 unbound** errors, with per-file counts retained in the artifact;
- the three receipt-bound errors are in `strategy_edge_validation.py` (1) and `strategy_research_loop.py` (2). PR #518 intentionally closed without merge after exact-head CI proved that changing `strategy_edge_validation.py` breaks the immutable preparation-receipt hash; no receipt or frozen evidence was modified;
- the 62 unbound errors are concentrated in seven runtime modules: `portfolio/admission_v0_1.py` (16), `paper/live_v0_1.py` (14), `training/detailed.py` (10), `paper/run_coordinator_v0_1.py` (8), `binance/funding_materializer_v0_2.py` (7), `paper/run_recovery_v0_1.py` (6), and `provider_metadata_capture_v0_2.py` (1);
- direct source cleanup must now exclude receipt-bound paths first, then choose a characterized unbound slice. Do not touch `training/detailed.py` before the 2026-09-27 natural Weekly Training evidence is reviewed; execution-sensitive Paper / Portfolio / Provider paths need focused characterization before edits;
- dedicated semantic dead-code tooling beyond the current conservative heuristic.

Do not make these blocking until baseline noise is measured and reviewed. Receipt-bound classification is cleanup guidance only; it does not hide errors or grant permission to mutate frozen artifacts.

### TD-008 — Dependency/security maintenance visibility

Status: **PARTIAL / SECURITY AND DEPENDENCY TRIAGE CURRENT**

Already implemented:

- `.github/dependabot.yml` tracks both `pip` and GitHub Actions monthly;
- update PRs are review-only; no auto-merge authority is introduced;
- repository-controlled CodeQL runs as non-blocking security visibility and has passed on current main;
- CI includes checksum-verified actionlint `1.7.12` for changed workflow files on pull requests;
- dedicated `security-visibility-dependencies.yml` uses pinned pip-audit `2.10.1` as informational / non-blocking dependency security visibility on every pull request and main push; it audits the frozen installed runtime dependency set and uploads CycloneDX JSON plus the audited requirements list for 30 days. PR #512 merged this path; main-push run `36214047453` succeeded and produced artifact `10896777315` with digest `sha256:cd4709f02c413289a6058e7f6365d0f1eedf8c87c903ece232e6655abfede14c`;
- Open PR Triage V0.7 records the completed dependency review; future proposals still require compatibility review;
- dependency classifications and vulnerability findings remain review guidance only and do not grant automatic remediation or merge authority.

Still missing:

- ongoing review of future dependency proposals and any pip-audit findings; the prior six-PR batch is complete under V0.7. No current open dependency backlog is inferred from the historical V0.5 record.

## P3 — code structure

### TD-009 — Large responsibility concentration in training modules

Status: **DEFERRED**

`training/quality.py` remains a responsibility-splitting candidate. First add characterization tests around current behavior; do not perform a behavior-changing rewrite solely for file size.

## Current cleanup order

Follow the dated checkpoint in `CURRENT_STATUS.md` and the [continuation runbook](PROJECT_CONTINUATION_RUNBOOK.md). These IDs extend this existing register; they add no execution authority. External waiting does not prevent independent eligible work.

| ID / priority | Checkpoint status | Next action | Completion evidence / boundary |
| --- | --- | --- | --- |
| TD-010 / P0 — Pages and Health | COMPLETE | Continue ordinary scheduled monitoring; reopen only on new evidence | Pages `35843351924` build/deploy/browser all SUCCESS; later natural Health `35870216734` on main `5b4aa2a...` was SUCCESS with `Overall: PASS`, `alerts: 0`, and dashboard backstop HEALTHY. No substitute dispatch was used. |
| TD-011 / P1 — Local reconciliation | EXCLUDED_BY_USER; HISTORICAL RECEIPT PRESERVED | No cloud cleanup action. Preserve [the reconciliation receipt](LOCAL_WORKSPACE_RECONCILIATION_2026_09_24.md); do not inspect, synchronize, delete, request or depend on user-local files | The earlier 78-path classification remains historical evidence only. C1/C4/C5 were integrated by PRs #493/#491/#492; C2/C3 remain deferred. Since 2026-09-25 the project is CLOUD_ONLY and local cleanup/recovery is explicitly excluded, so this item is not a current blocker or approval queue. |
| TD-012 / P1 — Training fingerprint | V0.2 BASELINE PUBLISHED; MODEL QUALITY REJECT; ONE-TIME AUTHORITY CONSUMED | Preserve comparison-only scheduled behavior; do not rerun bootstrap, loosen gates, migrate legacy pointers or infer promotion | PRs #504/#505 merged the versioned one-time authority and successor execution path. Bootstrap run `36110721415` completed `PASS / CORE100_FINGERPRINT_V0_2_BASELINE_PUBLISHED`; artifact `10860768638` records verified immutable-object and latest-pointer SHA-256 readback, zero provider requests and no holdout access. Model-quality gate remains `REJECT`; no threshold change, promotion, source switch or trading follows. |
| TD-013 / P1 — Delivery and PR review | MERGE VERIFIED THROUGH PR #512 | For every future delivery, resolve live main/open PRs and recheck exact head/base/checks; do not project historical PRs as current work | PR #509 merged Cloud Maintenance acceptance evidence at `1e5234fc`; PR #510 merged the evidence/data organization index at `463b9393`; PR #512 merged dependency audit / SBOM visibility at `25537c61`. #512 passed exact-head Python 3.12/3.13, workflow-static, dependency-security and CodeQL; post-merge main passed Python 3.12/3.13, Freeze Guard, dependency-security and CodeQL. Current delivery evidence does not grant execution or merge authority by itself. |
| TD-014 / P2 — Removed registrations | COMPLETE, 25/25 disabled (2026-09-25) | Keep the exact ID/path list and dated state readback in [Actions map](GITHUB_ACTIONS_OPERATING_MAP.md#removed-registrations-disabled-2026-09-25); reopen only if a listed registration is re-enabled | All 25 main paths returned 404; GitHub Actions UI showed success and Enable workflow for every target. Run history retained. Dependabot and source-preserved retired workflows untouched. |

After these items, continue TD-007 from fresh receipt-aware CI visibility: preserve all diagnostics, exclude receipt-bound artifacts from ordinary cleanup, and take only characterized unbound slices. Keep type/security informational. TD-009 responsibility splitting stays deferred until characterization coverage justifies it.

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
