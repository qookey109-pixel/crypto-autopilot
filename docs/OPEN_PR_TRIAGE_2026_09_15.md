# Open PR Triage — 2026-09-15

This document classifies currently open pull requests for operational navigation only. It does not replace Repository `main`, versioned configs/receipts, or immutable run evidence, and it does not authorize merge, provider access, R2 access, holdout access, promotion, formal trade plans, real-money orders, or live trading.

## Classification rules

- `ACTIVE`: directly relevant to the current September 15 execution path.
- `READY_NOT_MERGED`: validated and mergeable, but still requires explicit merge authority.
- `DEFERRED_STACK`: useful work that is not on the current P0 path and should not be treated as the next action.
- `REVIEW_REQUIRED_LEGACY_DRAFT`: unique legacy work preserved as Draft until deliberate salvage/rebuild review.
- `CLOSED_HISTORICAL_EVIDENCE`: closed without merge only after exact evidence bytes are proven to already exist on current `main`.
- `CLOSED_SUPERSEDED`: closed after file-level review proves current `main` already contains the implementation or a later governance-compatible evolution.

Never close a diverged PR merely because a newer feature looks similar. Close only after exact comparison proves it is fully superseded or after its unique content has been intentionally migrated.

## ACTIVE

| PR | Status | Role | Next action |
| --- | --- | --- | --- |
| #302 | Draft | Core100 post-training REJECT diagnosis and exact replay lineage | Wait for run `34936331199`; freeze/analyze replay evidence before any threshold/model change |
| #305 | Ready | Current-status/documentation convergence | Keep unmerged until explicit merge authority; this document is part of that governance package |
| #306 | Ready | Toolkit V0.2 REST/OpenAPI + Render origin + Cloudflare edge | CI passed; keep deployment/public exposure disabled and wait for explicit merge authority |

## DEFERRED_STACK

These PRs remain potentially useful but are not the current Core100 P0 path. Do not execute or merge them simply because they are open.

| PR | Role | Reason deferred |
| --- | --- | --- |
| #255 | Simulation readiness P0 / candle-driven V0.3 adapter | Separate simulation-readiness lane; requires comparison with current backtest/simulation code before revival |
| #257 | Prepared Pionex-native funding history protocol | Prepared protocol only; no production execution authority |
| #258 | Pionex historical reach discovery V0.3 | Public discovery lane; older base and not current Core100 blocker |
| #260 | Bounded Pionex 150+ universe snapshot execution package | Stacked on older Pionex universe work; requires stack reconstruction before use |
| #261 | Tiered Pionex 150+ history plan | Stacked planning stage; depends on older stacked PRs |
| #262 | Bounded Pionex funding capture execution package | Stacked execution authority proposal; should not be revived outside a fresh reviewed Pionex plan |

## CLOSED_HISTORICAL_EVIDENCE

| PR | Evidence proof | Result |
| --- | --- | --- |
| #256 | Its only two changed files match current `main` by exact Git blob SHA: evidence freeze `e36cd4d177f3e0e7eccd007dddd4080d9951b90a`; report `3b3262e14790f0082ae346b5d9bd4b788cc19cd1` | Closed without merge; no evidence lost |

## CLOSED_SUPERSEDED

| PR | File-level proof | Result |
| --- | --- | --- |
| #220 | 5/6 changed files match current `main` by exact Git blob SHA. The remaining config test is intentionally evolved on `main`: the old `no workflow exists` assertion became validation of a later separately versioned manual-only Context Forward Capture Execution Authority. | Closed without merge; original preparation functionality retained and later governance evolution preserved |
| #290 | Stale Core100 `8/10` handoff contradicted later verified History/Training state | Closed as superseded by current-status convergence |
| #301 | V0.1-only Toolkit REST/edge branch rebuilt cleanly from current `main` as V0.2 PR #306 | Closed as superseded by #306 |

## REVIEW_REQUIRED_LEGACY_DRAFT

These PRs all have unique content confirmed absent from current `main`. They were converted to Draft on 2026-09-15 so they remain preserved without looking ready to merge.

| PR | Unique content proof | State | Required treatment |
| --- | --- | --- | --- |
| #166 | `src/crypto_autopilot/market_structure.py` absent from current `main` | Draft | Salvage/rebuild Technical Analysis V0.2 intentionally from current main if revived |
| #167 | `src/crypto_autopilot/experiment_registry.py` absent from current `main` | Draft | Salvage lineage/registry/resource-planning primitives selectively |
| #168 | `src/crypto_autopilot/paper_simulation_demo.py` absent from current `main` | Draft | Review simulation-demo value against current canonical backtest/simulation path before migration |
| #199 | `src/crypto_autopilot/integrated_paper_strategy_v0_3.py` absent from current `main` | Draft | Large strategy/governance salvage review; do not merge old branch directly |
| #249 | `config/render_relay_502_remediation_review_v0_1.json` absent from current `main` | Draft | Preserve as bounded Render-diagnosis research until intentionally superseded or migrated |

## Current cleanup order

1. Do not disturb Core100 replay run `34936331199` while it is within its governed runtime window.
2. When replay completes, update #302 with frozen evidence and a reproducibility/threshold diagnosis.
3. Keep #305 and #306 ready but unmerged until explicit merge authority.
4. Reconstruct the #255/#257/#258/#260/#261/#262 Pionex stack from current `main` only if that lane becomes active again; do not merge the old stack directly.
5. Treat #166/#167/#168/#199/#249 as a salvage backlog, not current execution work.

## Safety boundary

Current project mode remains `PAPER-ONLY`. `source_switch_authorized=false`; replacement holdout remains `FROZEN_UNOPENED`; no automatic model promotion, formal trade plan, real-money order, live trading, paid cloud upgrade, provider substitution, or secret exposure is authorized by this triage.
