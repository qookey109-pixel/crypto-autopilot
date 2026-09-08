# Engineering Workflow V0.1

## Purpose

Add one lightweight planning and delivery path without creating a competing
authority system. The useful parts of `triage`, `to-spec`, `to-tickets` and
`wayfinder` from `mattpocock/skills` are four Work Item types, not four separate
project subsystems. No upstream skill bundle is vendored or required at runtime.

This document and every GitHub Issue remain planning artifacts. Repository
`main`, `PROJECT_STATUS.md`, the applicable versioned config and its receipt
remain the formal authority.

## Two-layer model

### Layer 1: formal authority

Controls provider access, R2 operations, holdout access, source switching,
model promotion, strategy/risk changes and all order paths. An authority change
requires a new versioned config and receipt, tests, a synchronized status update
and merge to `main`.

### Layer 2: engineering planning

Controls intake, clarification, specifications, task slices, dependencies,
verification and human review. It can prepare an authority proposal but cannot
activate or execute it.

## State meanings

| State | Meaning | Authority effect |
|---|---|---|
| `needs-triage` | Intake has not been classified | None |
| `needs-info` | Required evidence or decisions are missing | None |
| `ready-for-agent` | A bounded implementation slice is clear and testable | None |
| `ready-for-human` | Human decision, credential step or approval is needed | None |
| `evidence-ready` | Local/CI evidence is ready for review | None |
| `wontfix` | Planning item is closed without implementation | None |

`ready-for-agent` never means execution-authorized. A ticket can authorize local
code, tests and documentation within its stated scope; it cannot authorize an
external or governed operation.

## One Work Item, four types

| Type | Replaces | Required focus |
|---|---|---|
| `BUG_TRIAGE` | `triage` intake | observed/expected behavior and reproducible evidence |
| `SPECIFICATION` | `to-spec` output | outcome, scope, exclusions and acceptance evidence |
| `IMPLEMENTATION_TICKET` | `to-tickets` output | one vertical slice, blockers and verification |
| `DECISION_MAP` | `wayfinder` output | destination, child decisions and current frontier |

All four use `.github/ISSUE_TEMPLATE/work-item.yml`. A Work Item can change type
as information improves; it does not need to be copied into another workflow.

## Authority classification

Every implementation ticket must select one:

1. `PLANNING_ONLY`: local analysis, deterministic fixtures, docs or UI work.
2. `WITHIN_EXISTING_AUTHORITY`: cite the exact current config and receipt. The
   ticket still does not create authority.
3. `NEW_VERSIONED_AUTHORITY_REQUIRED`: only proposal, implementation scaffolding,
   synthetic tests and documentation may proceed. The gated operation stays off.

Use `authority-required` whenever the requested outcome mentions provider
access, R2 list/read/write, holdout evidence, source switching, model promotion,
strategy or risk changes, trade plans, Demo automation or live orders.

## Triage

1. Classify the item as bug, enhancement, decision or operational incident.
2. Reproduce or collect missing information without crossing authority.
3. Record expected outcome, affected boundary and current evidence.
4. Move to `ready-for-agent` only when the required ticket fields are complete.
5. Move to `ready-for-human` when permission, secrets, irreversible action or a
   product decision is required.

Issue closure and labels never modify `PROJECT_STATUS.md` or a receipt.

## Specification and ticket slicing

A specification should state user outcome, current behavior, scope, exclusions,
affected modules, authority classification and verification strategy.

Split it into vertical tracer-bullet tickets. Each ticket must:

- produce one observable outcome;
- fit one agent context where practical;
- declare blockers and downstream dependants;
- include acceptance checks and a runnable verification command;
- identify frozen-path impact;
- use expand/contract sequencing for wide refactors;
- preserve failure evidence instead of silently changing a threshold.

## Decision maps

Use a decision map for work too large or uncertain for one ticket. The parent
records the destination, constraints and frontier. Child tickets resolve one
decision each. Only unblocked decisions belong in the frontier.

A completed decision map can produce implementation tickets. It cannot promote
a model, open a holdout, activate a schedule or authorize an order.

## Templates

- `.github/ISSUE_TEMPLATE/work-item.yml`: the single bug/spec/ticket/map intake.
- `.github/pull_request_template.md`: implementation and authority review.

The canonical machine-readable contract is
`config/engineering_workflow_v0_1.json`.

## Branch convergence

`main` is the only long-lived branch and the only formal authority line.
Research stages, challengers and preparation states belong in versioned configs,
receipts and status documents, not permanent Git branches.

When branch protection requires a pull request, use one short-lived delivery
branch for the bounded change and remove it after merge. Existing branches or
worktrees must be audited against `origin/main` before any cleanup; unmerged or
dirty work is never deleted merely to satisfy this policy.

## Upstream provenance

Concepts were adapted from the MIT-licensed
[`mattpocock/skills`](https://github.com/mattpocock/skills) repository as
observed on 2026-08-27. The upstream repository is inspiration, not authority,
and future upstream updates are not imported automatically.
