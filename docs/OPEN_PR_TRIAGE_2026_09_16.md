# Open PR Triage — 2026-09-16

Snapshot authority base: `main=f5cf74292fca262ba72c4e0b36f8d757dfb82531`.

This is navigation and technical-debt classification only. It grants no merge or execution authority. Every PR must be rechecked against current `main` before a merge decision.

## Classification rules

- `ACTIVE_CURRENT` — branch is intentionally based on current main and is the active implementation lane.
- `REBUILD_FROM_CURRENT_MAIN` — work may still be valuable, but its base is old enough that historical CI is not sufficient merge evidence.
- `PRESERVE_DIAGNOSTIC_EVIDENCE` — evidence/result is valuable and must be retained; code/branch still requires current-main review.
- `SUPERSEDED_PENDING_PRESERVATION_PROOF` — newer work replaces the purpose, but keep open until all unique useful content is proven preserved.
- `SALVAGE_DRAFT` — unique old research exists, but the branch is not a merge candidate; revive only by rebuilding from current main.

## Current open PRs

### #322 — Governance: converge current operations and track technical debt

Classification: `ACTIVE_CURRENT`

- Base is exact reviewed current main `f5cf7429...`.
- This is the active control-plane/documentation-debt cleanup lane.
- Keep Draft until exact-head CI is green and cleanup scope is stable.
- No self-merge authority.

### #315 — Formalize Binance learning and Pionex execution-data roles

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Base `c99ccab...` predates the current Pionex validation/materialization changes.
- Its central architecture rule remains useful: Binance = large-scale learning database; Pionex = final calibration/execution-environment provenance.
- Parts of that rule are already represented in current main configs/workflows/status.
- Before preserving or closing, perform file-level comparison and salvage only content not already represented.

### #307 — AI Resource Hub statistical validation V0.1

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Base `7c5604e...` is older than current main.
- Native statistical edge-validation capability may remain useful.
- Historical green CI does not validate compatibility with current Toolkit/Pionex/control-plane state.
- If revived, rebuild or rebase-equivalent from current main and rerun exact-head CI.

### #306 — Toolkit REST API and Cloudflare edge V0.2

Classification: `REBUILD_FROM_CURRENT_MAIN`

- Base `7c5604e...` is older than current main.
- REST/OpenAPI and edge hardening may remain useful.
- Deployment/public exposure remain unauthorized.
- If revived, rebuild from current main; do not merge the historical head solely because old CI passed.

### #305 — September 15 current-operations convergence

Classification: `SUPERSEDED_PENDING_PRESERVATION_PROOF`

- Its design directly informed #322.
- #322 starts from current main instead of the older `7c5604e...` base.
- Useful concepts already reused: `CURRENT_STATUS.md`, machine-readable current state, agent read order, root-status convergence, PR triage, and regression guards.
- Keep #305 open until #322 proves all unique useful content is either preserved, intentionally superseded, or unnecessary.

### #302 — Core100 post-training REJECT diagnosis

Classification: `PRESERVE_DIAGNOSTIC_EVIDENCE`

- Exact replay run `34936331199` completed successfully.
- Dataset fingerprint was preserved.
- Evaluated threshold range `0.50-0.55` supports no threshold change.
- The branch base is old; do not merge blindly.
- Preserve the immutable diagnostic receipt/result and review code hardening separately against current main.

### #249 — Bounded Render Relay 502 Review Authority

Classification: `SALVAGE_DRAFT`

- Historical incident-review proposal only.
- No runtime or remediation authority.
- Retain as salvage evidence unless a new current-main incident-review version is needed.

### #199 — Integrated Paper Strategy / Promotion Governance V0.3

Classification: `SALVAGE_DRAFT`

- Contains unique strategy/promotion research design.
- Built against a much older main generation.
- Not a merge candidate; future revival should cherry-pick ideas, not the old branch wholesale.

### #168 — Deterministic Paper Simulation Demo

Classification: `SALVAGE_DRAFT`

- Useful deterministic simulation demonstration may remain as research reference.
- Old branch is not a merge candidate.

### #167 — Offline Research Governance Layer

Classification: `SALVAGE_DRAFT`

- Useful lineage/registry/resource-aware research patterns may remain valuable.
- Rebuild selected patterns from current main if needed.

### #166 — Technical Analysis Foundation V0.2

Classification: `SALVAGE_DRAFT`

- Unique feature-engineering and causal multi-timeframe work may remain useful.
- Branch predates many current architecture changes.
- Rebuild selected components from current main if revived.

## Cleanup order

1. Get #322 exact-head CI green.
2. Finish current-status/security/root-doc convergence in #322.
3. Compare #305 unique files against #322 and close #305 only after preservation proof.
4. Compare #315 against current Pionex architecture and absorb only unique missing governance content.
5. Decide whether #302 hardening is still needed after its immutable result is preserved.
6. Rebuild #306/#307 from current main only if those capabilities remain priorities.
7. Leave #166/#167/#168/#199/#249 as Draft salvage backlog unless explicitly revived.

## Non-authority

This triage does not authorize merges, workflow dispatches, provider calls, R2 writes, holdout access, source switching, model promotion, trade plans, real-money orders, live trading, deployment, or public exposure.
