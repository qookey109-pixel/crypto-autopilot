# Open PR Triage — 2026-09-15

This document classifies currently open pull requests for operational navigation only. It does not replace Repository `main`, versioned configs/receipts, or immutable run evidence, and it does not authorize merge, provider access, R2 access, holdout access, promotion, formal trade plans, real-money orders, or live trading.

## Classification rules

- `ACTIVE`: directly relevant to the current September 15 execution path.
- `READY_NOT_MERGED`: validated and mergeable, but still requires explicit merge authority.
- `DEFERRED_STACK`: useful work that is not on the current P0 path and should not be treated as the next action.
- `REVIEW_REQUIRED_LEGACY`: older/diverged work whose unique functionality must be compared against current `main` before close/rebuild.
- `HISTORICAL_EVIDENCE_CANDIDATE`: evidence-only work that may be retained as history or frozen separately after confirming its evidence is already preserved on current `main`.

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

## HISTORICAL_EVIDENCE_CANDIDATE

| PR | Role | Review rule |
| --- | --- | --- |
| #256 | Freeze Pionex bounded pilot V0.2 PASS evidence | Confirm receipt/report evidence is already preserved on current `main` before closing as historical |

## REVIEW_REQUIRED_LEGACY

These branches are old enough or diverged enough that ancestry alone does not prove supersession. Preserve until a functional/file-level comparison is completed.

| PR | Role | Main risk if closed blindly |
| --- | --- | --- |
| #166 | Technical Analysis Foundation V0.2 | May contain unique EMA200/structure/multi-timeframe feature work |
| #167 | Offline research governance layer | May contain unique lineage/registry/resource-aware governance primitives |
| #168 | Deterministic paper simulation demo | May contain unique execution-lifecycle fixtures or tests |
| #199 | Integrated Paper Strategy / promotion governance V0.3 | Large strategy/governance branch; requires deliberate migration review |
| #220 | Context forward capture V0.1 | May contain unique CoinPaprika/context capture preparation |
| #249 | Render relay 502 bounded review authority | Likely historical, but verify later Render evidence/remediation fully supersedes it before closure |

## Already cleaned in this pass

- PR #290: stale `8/10` documentation handoff — closed as superseded.
- PR #301: Toolkit REST/edge V0.1 — rebuilt from current `main` as V0.2 PR #306, then closed as superseded.

## Current cleanup order

1. Do not disturb Core100 replay run `34936331199` while it is within its governed runtime window.
2. When replay completes, update #302 with frozen evidence and a reproducibility/threshold diagnosis.
3. Keep #305 and #306 ready but unmerged until explicit merge authority.
4. Review #256 for evidence preservation and close only if current `main` already contains equivalent immutable receipts.
5. Reconstruct the #255/#257/#258/#260/#261/#262 Pionex stack from current `main` only if that lane becomes active again; do not merge the old stack directly.
6. Perform file-level salvage review for #166/#167/#168/#199/#220/#249 before any closure.

## Safety boundary

Current project mode remains `PAPER-ONLY`. `source_switch_authorized=false`; replacement holdout remains `FROZEN_UNOPENED`; no automatic model promotion, formal trade plan, real-money order, live trading, paid cloud upgrade, provider substitution, or secret exposure is authorized by this triage.
