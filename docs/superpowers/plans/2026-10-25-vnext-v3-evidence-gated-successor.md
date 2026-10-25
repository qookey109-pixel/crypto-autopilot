# VNext V3 Evidence-Gated Successor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans, test-driven-development, systematic-debugging and verification-before-completion. Each batch is a separate release gate.

**Goal:** Deliver a falsifiable V3 market research/decision dashboard on top of current merged main, without authenticating unverified source archives or starting PAPER execution.

**Architecture:** Maintain static build-time HTML projections from versioned JSON and strict pure validators. GitHub Actions alone runs Python tests, Pages built-site Playwright and post-merge browser-production. Research display is a read-only surface, not a strategy, writer or execution API.

**Tech Stack:** Python 3.12/3.13, JSON, existing HTML/CSS/JS, Playwright (Chromium), GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-25-vnext-v3-evidence-gated-design.md`

## Global Constraints
CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY. Resolve latest main, open PR exact heads/base/checks each batch. No local machine operations, provider/R2/D1/secret access in this branch. #810 exact hash required. No real-money/live trading or holdout/promotion/source switch. No re-run of consumed one-time Billing/Usage/bootstrap. Never call an unexecuted formal Paper decision NO_TRADE.

## Review Focus
- [ ] Unverified artifact identity or malformed digest fails closed and does not increase 16/21.
- [ ] GitHub run creation, artifact creation, source candle and site publication are visibly different time types.
- [ ] Missing/revised/invalid strategy registry cannot produce `NO_ELIGIBLE_STRATEGY` as an actual executed Paper outcome.
- [ ] Zero, null and missing data semantics remain distinct; no made-up live quote, fee, account result or profitability.
- [ ] 390px phone/keyboard, external research links and strict hash equality regressions stay green.

### Task 1 — P0 Metadata provenance projection
**Files:** create `research/status/vnext-shadow-observed-metadata-2026-10-25-v0-1.json`; test `tests/test_delivery_overview.py`; modify `scripts/build_delivery_overview.py`.
- [ ] RED: commit focused tests requiring strict observed run/artifact metadata, separate time semantics, fail-closed invalid input and no 17th verified batch; observe cloud CI failure for missing feature.
- [ ] GREEN: add versioned run/artifact metadata from exact GitHub read-only response and pure validator/HTML build; confirm Python 3.12/3.13 cloud CI green.
- [ ] Browser: add Playwright assertions for observed-vs-validated provenance, evidence source links, keyboard open/close and mobile overflow; confirm Pages PR built-site tests.
- [ ] Record actual CI/Pages PR job IDs and head.

### Task 2 — P0 Design-time NO_ELIGIBLE_STRATEGY
**Files:** same Python builder, registry `config/cloud_paper_strategy_registry_v0_1.json` read-only, tests in `tests/test_delivery_overview.py`.
- [ ] RED: require literal separation `NOT_RUN（非 NO_TRADE）` and `僅設計時原因：NO_ELIGIBLE_STRATEGY` on valid versioned empty registry; invalid/missing registry to UNKNOWN.
- [ ] GREEN: implement strict versioned registry predicate, preserve generated page fallback/no prior production report; validate Python and Playwright.
- [ ] Do not change actual strategy registry, cash genesis, execution config or official schedule.

### Task 3 — Product+release acceptance
**Files:** existing `web/index.html`, `web/assets/css/styles.css`, `tests/browser/dashboard.spec.cjs`, `docs/VNEXT_DELIVERY_WORK_ORDER_2026_10_09.md` (source reference, do not erase historic).
- [ ] Keep manual EasyRead/Yaozi/Clef first-screen links and required V3 research/status cards. Existing System section retains engineering results.
- [ ] 390px width no unintended horizontal overflow and keyboard-operable disclosures; preserve mobile vertical cards.
- [ ] Check exact-head PR CI/CodeQL/SBOM and Pages build + browser test. A PR build only has deploy/browser-production `skipped`; mark explicitly.
- [ ] Do not merge without separate approval; after approval resolve new main, then verify real Pages desktop/mobile + SHA-256 gate (not source-only CI).

### Task 4 — Later P0 original-data integrity
**Files:** existing `src/crypto_autopilot/research/prospective_shadow_continuity_v0_1.py`, PR #809 feature-coverage successor or later isolated branch, a dated original ZIP receipt.
- [ ] Review actual existing scheduled archive ZIPs using GitHub-hosted read-only execution if permitted. Independently prove run/attempt/artifact digest, embedded identity, candle closes, 60m causality and features before incrementing batch count.
- [ ] If original archive bytes cannot be authenticated, record `UNVERIFIED`; never promote metadata-only observations.
- [ ] Test missing, null and 15m/4h absent; costs/overlap and rolling Shadow separately.

### Task 5 — Later P0 safe formal PAPER authority
**Files:** versioned Cloudflare shared-writer, billable-usage, D1/query, slot/prepaid and paper-loop contracts; reuse existing synthetic test suite.
- [ ] Reconcile all repository writers, independent account evidence/limits and finite D1 reservation/recovery.
- [ ] Preserve $10,000 genesis, empty registry and unchanged model-quality REJECT. Don't invent an executed NO_TRADE before actual main report.
- [ ] Distinct user authorization is mandatory before external D1 provisioning, any new active PAPER execution authority, finite natural schedule or payment-related call; verify actual first natural run separately.
