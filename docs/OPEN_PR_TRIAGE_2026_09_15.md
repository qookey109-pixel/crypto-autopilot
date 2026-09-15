# Open PR Triage — 2026-09-15

This document classifies pull requests for operational navigation only. It does not replace Repository `main`, versioned configs/receipts, or immutable run evidence, and it does not authorize merge, provider access, R2 access, holdout access, promotion, formal trade plans, real-money orders, or live trading.

## Classification rules

- `ACTIVE`: directly relevant to the current September 15 path.
- `REVIEW_REQUIRED_LEGACY_DRAFT`: unique legacy work preserved as Draft until deliberate salvage/rebuild review.
- `CLOSED_ALREADY_PRESERVED_ON_MAIN`: closed only after exact file/core-behavior verification proves current `main` already contains the work.
- `CLOSED_HISTORICAL_EVIDENCE`: evidence-only PR closed after exact evidence bytes are proven on `main`.
- `CLOSED_SUPERSEDED`: current `main` contains the implementation plus a later compatible/safety evolution.

Never close a diverged PR merely because a newer feature looks similar.

## ACTIVE

| PR | Status | Role | Next action |
| --- | --- | --- | --- |
| #302 | Draft | Core100 post-training REJECT diagnosis and exact replay lineage | Wait for run `34936331199`; freeze/analyze replay evidence before threshold/model changes |
| #305 | Ready | Current-status/documentation convergence | Validate latest exact head; keep unmerged until explicit merge authority |
| #306 | Ready | Toolkit V0.2 REST/OpenAPI + Render origin + Cloudflare edge | CI passed; deployment/public exposure remain disabled; keep unmerged until explicit merge authority |

## CLOSED_ALREADY_PRESERVED_ON_MAIN

| PR | Proof | Result |
| --- | --- | --- |
| #255 | V0.3 config/docs/prepared receipt/readiness module and all dedicated regression tests match `main`; its backtest/risk hardening behavior is present on `main` | Closed without merge |
| #257 | All 5 funding-history protocol files exact-match `main` | Closed without merge |
| #260 | All 6 Pionex 150+ universe execution files exact-match `main` | Closed without merge |
| #261 | All 5 tiered 150+ history planner files exact-match `main` | Closed without merge |
| #262 | All 5 bounded funding-capture execution files exact-match `main` | Closed without merge |

## CLOSED_HISTORICAL_EVIDENCE

| PR | Evidence proof | Result |
| --- | --- | --- |
| #256 | Both changed files match current `main` by exact Git blob SHA: evidence freeze `e36cd4d177f3e0e7eccd007dddd4080d9951b90a`; report `3b3262e14790f0082ae346b5d9bd4b788cc19cd1` | Closed without merge; no evidence lost |

## CLOSED_SUPERSEDED

| PR | File-level proof | Result |
| --- | --- | --- |
| #220 | 5/6 changed files exact-match `main`; remaining test is a later governance evolution validating the separately versioned manual-only execution authority | Closed without merge |
| #258 | Reach authority assets are on `main`; main adds stricter cutoff-close logic, safe diagnostics and aggregate interval-failure behavior | Closed without merge; later safety fixes preserved |
| #290 | Stale Core100 `8/10` handoff contradicted later verified History/Training state | Closed as superseded |
| #301 | V0.1-only Toolkit REST/edge branch rebuilt from current `main` as V0.2 PR #306 | Closed as superseded by #306 |

## REVIEW_REQUIRED_LEGACY_DRAFT

These PRs have unique content confirmed absent from current `main`. They are Draft so they remain preserved without looking ready to merge.

| PR | Unique content proof | State | Required treatment |
| --- | --- | --- | --- |
| #166 | `src/crypto_autopilot/market_structure.py` absent from current `main` | Draft | Salvage/rebuild Technical Analysis V0.2 intentionally from current main if revived |
| #167 | `src/crypto_autopilot/experiment_registry.py` absent from current `main` | Draft | Salvage lineage/registry/resource-planning primitives selectively |
| #168 | `src/crypto_autopilot/paper_simulation_demo.py` absent from current `main` | Draft | Review simulation-demo value against the canonical current backtest/simulation path |
| #199 | `src/crypto_autopilot/integrated_paper_strategy_v0_3.py` absent from current `main` | Draft | Large strategy/governance salvage review; do not merge old branch directly |
| #249 | `config/render_relay_502_remediation_review_v0_1.json` absent from current `main` | Draft | Preserve until intentionally superseded or migrated |

## Cleanup result

The old Pionex/Simulation stacked chain #255/#257/#258/#260/#261/#262 is no longer an open operational backlog. Every closure was preceded by exact preservation or supersession verification. If that research lane is revived later, design the next version from then-current `main` rather than reopening or merging the old stack.

The expected remaining open PR set is now exactly:

`#166, #167, #168, #199, #249, #302, #305, #306`

## Current cleanup order

1. Do not disturb Core100 replay run `34936331199` while it is within its governed runtime window.
2. When replay completes, update #302 with frozen evidence and reproducibility/threshold diagnosis.
3. Keep #305 and #306 ready but unmerged until explicit merge authority.
4. Treat #166/#167/#168/#199/#249 as a salvage backlog, not current execution work.

## Safety boundary

Current project mode remains `PAPER-ONLY`. `source_switch_authorized=false`; replacement holdout remains `FROZEN_UNOPENED`; no automatic model promotion, formal trade plan, real-money order, live trading, paid cloud upgrade, provider substitution, or secret exposure is authorized by this triage.
