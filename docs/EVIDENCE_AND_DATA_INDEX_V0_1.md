# Evidence and Data Index V0.1

This index organizes repository evidence without changing authority, execution behavior, or historical lineage.

Repository `main` remains the current authority and must be resolved live before acting. This file is a navigation and retention map only. It does not authorize provider access, R2 access, holdout access, training, promotion, source switching, trade plans, real-money orders, or live trading.

## Read order

Use this order for current work:

1. `CURRENT_STATUS.md` — concise current operations state and ordered checkpoint.
2. `research/status/current-operations-v0-3.json` — machine-readable companion to current operations.
3. `PROJECT_STATUS.md` — formal project stage, governance, compatibility, and retired-workflow context.
4. `AGENTS.md` — coding-agent execution and safety rules.
5. `docs/PROJECT_CONTINUATION_RUNBOOK.md` — operational continuation, evidence format, and acceptance rules.
6. `docs/GITHUB_ACTIONS_OPERATING_MAP.md` — current schedule / manual / historical workflow map.
7. The exact versioned config and immutable receipt referenced by the stage being changed.
8. GitHub Actions metadata and run artifacts for run-specific evidence.

If any dated document conflicts with live `main`, live `main` wins. Historical files remain evidence; they do not become current merely because they are easier to find.

## Evidence classes

| Class | Typical paths | Role | Cleanup rule |
| --- | --- | --- | --- |
| CURRENT AUTHORITY ENTRYPOINT | `CURRENT_STATUS.md`, `PROJECT_STATUS.md`, `AGENTS.md` | Current navigation, governance and work order | May be updated only by reviewed current-state work; resolve live `main` first |
| MACHINE-READABLE CURRENT STATUS | `research/status/current-operations-v0-3.json` | Structured companion to current operations | Treat older `research/status/*` versions as historical unless explicitly promoted |
| VERSIONED CONTRACT / CONFIG | `config/*.json`, versioned contract docs | Defines bounded behavior and authority | Never silently edit history; create a new version when semantics change |
| IMMUTABLE RECEIPT / EVIDENCE | `research/receipts/*` | Frozen result, authority transition, observation, or run evidence | Do not rewrite, rename, move, squash, or delete as routine cleanup |
| RUN EVIDENCE | GitHub Actions run IDs, attempts, jobs, artifacts | Exact execution evidence | Preserve exact run / attempt / SHA references; do not replace natural runs with manual reruns |
| HISTORICAL SNAPSHOT | dated `docs/*2026_*.md`, superseded handoffs / triage docs | Historical review context | Keep in place; add pointers instead of rewriting the snapshot |
| DERIVED PROJECTION | `web/data/*`, dashboard projections, generated maintenance blocks | Read-only presentation derived from authority | Never treat as independent research authority; generated blocks should not be hand-edited |
| ESTIMATE / BUDGET | `research/estimates/*`, budget configs/docs | Planning and cost constraints | Not execution or market-data authority |

## Directory map

### `research/receipts/`

Immutable evidence store. It contains authority grants, prepared states, observations, completion receipts, failure evidence, and run reports.

Rules:

- keep exact historical filenames and paths;
- preserve failed, blocked, rejected, and superseded evidence;
- never convert a prepared receipt into an executed result by editing it;
- never delete a receipt because a newer version exists;
- use a new receipt for a new decision, run, or authority transition;
- link from current status or this index instead of moving files into archive folders.

See `research/receipts/README.md` for the local receipt-specific rules.

### `research/status/`

Structured status snapshots and current-operation companions.

- `current-operations-v0-3.json` is the current machine-readable companion named by root documentation.
- other versioned status files remain useful lineage unless current documentation explicitly identifies them as active.
- status JSON does not override repository `main` or the exact underlying receipt / run evidence.

### `config/`

Versioned contracts, schedule projections, gates, and bounded authority definitions.

Cleanup must preserve exact version identity. A newer config can supersede an older one operationally, but the older config remains lineage evidence.

### `docs/`

Contains both current guides and historical snapshots.

Current navigation documents include:

- `PROJECT_CONTINUATION_RUNBOOK.md`
- `GITHUB_ACTIONS_OPERATING_MAP.md`
- `PROJECT_MAP_V0_1.md`
- `AUTOMATION_INDEX_V0_1.md`
- `STRATEGY_INDEX_V0_1.md`
- `TECH_DEBT_REGISTER_2026_09_17.md`

Dated handoffs, triage files, blocker snapshots, and historical review notes should normally remain in place. Prefer linking and classification over physical relocation because exact paths may be referenced by tests, docs, receipts, or historical commits.

### `web/data/`

Read-only dashboard projection data. It is a presentation surface, not an independent authority source.

If web projection conflicts with current repository authority, repair the projection generator or current projection layer; do not reinterpret historical evidence to match the page.

## Current retention rules

The following categories are protected from routine cleanup:

- frozen configs and receipts;
- Core100 V0.2 baseline evidence and one-time bootstrap authority/result;
- model-quality `REJECT` evidence and threshold-replay evidence;
- replacement-holdout frozen state;
- source-switch and provider provenance boundaries;
- GitHub Actions run / attempt references used for natural schedule acceptance;
- generated Cloud Maintenance evidence blocks;
- historical failure and blocked-permission evidence.

Deletion is appropriate only for clearly disposable generated assets or redundant non-authoritative files after confirming no tests, workflows, docs, receipts, or historical compatibility depend on the exact path.

## Naming guidance for new evidence

Prefer names that expose date, subject, version, and evidence role:

`YYYY-MM-DD-<subject>-vX-Y-<role>.json`

Examples of roles already used in the repository include:

- `authority`
- `prepared`
- `completion`
- `observation`
- `report`
- `evidence-freeze`
- `failure-evidence`

Do not rename old files merely to match this guidance.

## Cleanup workflow

For future organization work:

1. resolve live `main` and open PRs;
2. classify the target as current authority, versioned contract, immutable evidence, historical snapshot, or derived projection;
3. search references before moving or deleting anything;
4. prefer an index/link update over physical relocation;
5. keep evidence-bearing changes separate from engineering behavior changes;
6. run ordinary CI and governance checks;
7. recheck exact head/base and live `main` before merge.

## 2026-09-26 organization snapshot

At the reviewed baseline `1e5234fc7b37572a178ee6d06b10214a50263258`, the repository tree contained 1,316 files. A broad path/name scan identified roughly 450 files related to docs, status, receipts, evidence, schedules, or runbooks.

Those counts are a dated organization snapshot only; they are not a repository invariant and should not be used as a gate.

The cleanup conclusion from this snapshot is intentionally conservative: improve discovery and classification first, while leaving immutable evidence and compatibility-sensitive paths where they are.
