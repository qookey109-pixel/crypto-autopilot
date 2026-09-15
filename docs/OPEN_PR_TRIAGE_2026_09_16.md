# Open PR Triage — 2026-09-16

Repository `main` is authority and must be resolved live before every merge decision. Evidence-basis parent for this triage version: `a8f64ca1b2ecfbec6e6d9769fa3726dc007aa266` after PR #322 merged. This SHA is not a latest-main claim.

This is navigation and technical-debt classification only. It grants no merge or execution authority.

Machine-readable companion: `research/status/open-pr-triage-v0-3.json`.

## Classification rules

- `ACTIVE_CURRENT` — branch is intentionally based on the reviewed parent main and is the active implementation lane.
- `REBUILD_FROM_CURRENT_MAIN` — work may still be valuable, but its base is old enough that historical CI is not sufficient merge evidence.
- `PRESERVE_DIAGNOSTIC_EVIDENCE` — evidence/result is valuable and must be retained; code/branch still requires current-main review.
- `SUPERSEDED_PENDING_PRESERVATION_PROOF` — newer work replaces the purpose, but keep open until all unique useful content is proven preserved.
- `SALVAGE_DRAFT` — unique old research exists, but the branch is not a merge candidate; revive only by rebuilding from current main.

## Active current lane

### #323 — Dashboard: wire Current Operations V0.3 after historical authority

Classification: `ACTIVE_CURRENT`

- Base parent main: `a8f64ca1...`, the PR #322 merge commit.
- Removes the self-referential latest-main status bug.
- Wires Current Operations V0.3 into the production Dashboard/Pages projection after frozen historical authority.
- Stops the homepage deployment generator from restoring September 13 `8/10 / Training skipped / PR #292` present-tense state.
- Keep Draft until exact-head CI, Pages, Zh-Hant snapshot, Static Smoke, and regression guards are green.
- No merge authority is granted by this triage.

## Recently merged

### #322 — Governance: converge current operations and track technical debt

Outcome: `MERGED_POST_MERGE_CI_PAGES_FREEZE_GUARD_GREEN`

- Merge commit: `a8f64ca1b2ecfbec6e6d9769fa3726dc007aa266`.
- Established the first current-status/control-plane convergence batch.
- Replaced hard-coded schedule-count health assertions with inventory-derived checks.
- Published the first current-main PR triage and Dashboard current overlay prototype.
- #323 is the focused projection follow-up, not a retry of #322.

## Other open PRs

### #315 — Formalize Binance learning and Pionex execution-data roles

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Base `c99ccab...` predates current Pionex validation/materialization changes.
- Central architecture rule remains useful: Binance = large-scale learning database; Pionex = final calibration/execution-environment provenance.
- Compare at file level and salvage only unique content not already represented.

### #307 — AI Resource Hub statistical validation V0.1

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Base `7c5604e...` is older than current main.
- Native statistical edge-validation capability may remain useful.
- Rebuild from current main and rerun exact-head CI if revived.

### #306 — Toolkit REST API and Cloudflare edge V0.2

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Base `7c5604e...` is older than current main.
- REST/OpenAPI and edge hardening may remain useful.
- Deployment/public exposure remain unauthorized.
- Rebuild from current main if revived.

### #305 — September 15 current-operations convergence

Classification: `SUPERSEDED_PENDING_PRESERVATION_PROOF`

- Its design informed merged #322 and current #323.
- Useful concepts already preserved include Current Status, machine-readable state, agent read order, root-status convergence, PR triage, and regression guards.
- Compare any remaining unique content against merged #322/current #323 before closing.

### #302 — Core100 post-training REJECT diagnosis

Classification: `PRESERVE_DIAGNOSTIC_EVIDENCE`

- Exact replay run `34936331199` completed successfully.
- Dataset fingerprint was preserved.
- Evaluated threshold range `0.50-0.55` supports no threshold change.
- Preserve immutable diagnostic evidence and review code hardening separately against current main.

### #249 — Bounded Render Relay 502 Review Authority

Classification: `SALVAGE_DRAFT`

- Historical incident-review proposal only.
- No runtime or remediation authority.

### #199 — Integrated Paper Strategy / Promotion Governance V0.3

Classification: `SALVAGE_DRAFT`

- Contains unique strategy/promotion research design.
- Old branch is not a merge candidate; revive selected ideas from current main only.

### #168 — Deterministic Paper Simulation Demo

Classification: `SALVAGE_DRAFT`

- Useful deterministic simulation reference.
- Old branch is not a merge candidate.

### #167 — Offline Research Governance Layer

Classification: `SALVAGE_DRAFT`

- Useful lineage/registry/resource-aware patterns may remain valuable.
- Rebuild selected patterns from current main if needed.

### #166 — Technical Analysis Foundation V0.2

Classification: `SALVAGE_DRAFT`

- Unique feature-engineering and causal multi-timeframe work may remain useful.
- Rebuild selected components from current main if revived.

## Cleanup order

1. Get #323 exact-head CI / Pages / Zh-Hant / Static Smoke green.
2. Merge #323 only after separate explicit exact-head authorization.
3. Compare #305 unique files against merged #322 and #323, then close only after preservation proof.
4. Compare #315 against current Pionex architecture and absorb only unique missing governance content.
5. Decide whether #302 code hardening is still needed after immutable diagnostic evidence is preserved.
6. Rebuild #306/#307 from current main only if those capabilities remain priorities.
7. Leave #166/#167/#168/#199/#249 as Draft salvage backlog unless explicitly revived.

## Non-authority

This triage does not authorize merges, workflow dispatches, provider calls, R2 writes, holdout access, source switching, model promotion, trade plans, real-money orders, live trading, deployment, or public exposure.
