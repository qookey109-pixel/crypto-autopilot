# Open PR Triage — 2026-09-17

Repository `main` is authority and must be resolved live before every merge decision. Evidence-basis parent for this triage version: `59be8326cb822cd2e618f537c8bbf24b2621af37` after PR #340 merged. This SHA is not a latest-main claim.

This document is navigation only. It grants no merge, workflow-dispatch, provider, R2, holdout, source-switch, promotion, deployment, order, or live-trading authority.

Machine-readable companion: `research/status/open-pr-triage-v0-4.json`.

## Classification rules

- `SUPERSEDED_OLD_BASE` — purpose is already satisfied by newer merged work; do not merge the old branch. Close only after confirming no unique useful content remains.
- `REBUILD_FROM_CURRENT_MAIN` — capability may still be useful, but historical CI/base is insufficient; rebuild selectively from current `main`.
- `EVIDENCE_PRESERVED_CODE_REVIEW_ONLY` — immutable result/evidence is already on `main`; only unique implementation hardening remains eligible for review.
- `DEPENDENCY_REVIEW` — automated dependency update; review compatibility and exact-head CI separately. No auto-merge authority.
- `SALVAGE_DRAFT` — unique older research may remain useful, but the old branch itself is not a merge candidate.

## Superseded old-base lane

### #336 — Record Pionex V0.2 materialization PASS and converge current status

Classification: `SUPERSEDED_OLD_BASE`

- Base: `5eaf57133d013fad030681182b379a02d915766e`.
- Its completion-evidence purpose is already covered by merged PR #337.
- Its current-status/dashboard convergence purpose is already covered by merged PR #339.
- Do not merge #336 from its old base.
- Before closing, confirm its proposed extra receipt/status edits add no unique evidence beyond #337/#339.

## Rebuild-from-current-main lane

### #315 — Formalize Binance learning and Pionex execution-data roles

Classification: `REBUILD_FROM_CURRENT_MAIN`

- The central architecture rule remains useful: Binance USD-M = large-scale learning database; Pionex = final calibration/execution-environment provenance.
- The branch predates completed Pionex V0.2 materialization and contains stale `not materialized` wording.
- Salvage only still-missing governance content from its four changed files; do not merge the branch directly.

### #307 — AI Resource Hub statistical validation V0.1

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Native statistical edge-validation capability may remain useful.
- Rebuild from current main only if this capability remains a priority; preserve all current authority boundaries.

### #306 — Toolkit REST API and Cloudflare edge V0.2

Classification: `REBUILD_FROM_CURRENT_MAIN`

- REST/OpenAPI and edge-hardening work may remain useful.
- Deployment and public exposure remain unauthorized.
- Rebuild from current main only if revived.

## Evidence-preserved code-review lane

### #302 — Core100 post-training REJECT diagnosis

Classification: `EVIDENCE_PRESERVED_CODE_REVIEW_ONLY`

- The four immutable diagnosis/threshold receipts from #302 were preserved byte-for-byte on `main` by PR #340.
- Threshold replay remains `supported_thresholds=[]`; configured threshold remains `0.55`; Model Quality remains `REJECT`.
- The old one-shot authority is expired and consumed.
- Remaining value, if any, is limited to unique diagnostics/code hardening and tests. Review those files against current main before selectively rebuilding anything.
- Do not use #302 to reopen R2 diagnostic reads, retraining, holdout, threshold changes, promotion, source switch, or trading.

## Dependency-review lane

The repository already has monthly Dependabot visibility for both `pip` and GitHub Actions. These PRs are review-only and each requires its own current-main compatibility review and merge decision.

- #326 — boto3 `1.43.75 -> 1.43.93`
- #327 — actions/cache `5.1.0 -> 6.1.0`
- #328 — actions/download-artifact `7.0.0 -> 8.0.1`
- #329 — ruff `0.16.0 -> 0.16.7`
- #330 — actions/checkout `6 -> 7`
- #331 — pyarrow `21.0.0 -> 25.0.1`

Major-version changes should be treated as higher compatibility risk than routine patch/minor updates. Historical Dependabot checks are not merge authority.

## Salvage drafts

### #249 — Bounded Render Relay 502 Review Authority

Classification: `SALVAGE_DRAFT`

Historical incident-review proposal only. No runtime/remediation authority.

### #199 — Integrated Paper Strategy / Promotion Governance V0.3

Classification: `SALVAGE_DRAFT`

Contains strategy/promotion research design. Rebuild selected ideas only from current main if deliberately revived.

### #168 — Deterministic Paper Simulation Demo

Classification: `SALVAGE_DRAFT`

Useful deterministic simulation reference; old branch is not a merge candidate.

### #167 — Offline Research Governance Layer

Classification: `SALVAGE_DRAFT`

Useful lineage/registry/resource-aware patterns may remain valuable; selectively rebuild only if needed.

### #166 — Technical Analysis Foundation V0.2

Classification: `SALVAGE_DRAFT`

Unique feature-engineering and causal multi-timeframe work may remain useful; old branch is not a merge candidate.

## Recently resolved references

- #305: closed without merge; its current-status purpose was superseded by later convergence work.
- #323: merged as the Dashboard/Homepage Current Operations V0.3 projection fix.
- #337: merged Pionex V0.2 materialization completion evidence.
- #338: merged Research Automation Health report-contract repair.
- #339: merged Pionex V0.2 current-status/dashboard convergence.
- #340: merged Core100 REJECT / threshold-replay evidence preservation.

## Cleanup order

1. Preserve #340 as the evidence boundary; review #302 code separately rather than reviving its authority.
2. Compare #336 against merged #337/#339 and close it only after confirming no unique useful content remains.
3. Compare #315's four files against current main and salvage only still-missing provenance/governance content.
4. Review Dependabot PRs independently, prioritizing compatibility analysis for major-version jumps.
5. Rebuild #306/#307 from current main only if they remain priorities.
6. Keep #166/#167/#168/#199/#249 as Draft salvage unless deliberately revived.

No item in this triage is self-authorized to merge or close another PR.
