# Core100 Fingerprint V0.2 Cloud Collector Prototype

Status: IMPLEMENTATION_PREPARED_NOT_ACTIVE  
Evidence basis: main b150c965bbcbc8bbb1a86824acd61b93eec519bf  
Prepared: 2026-09-25 04:01:21 UTC

## Scope

This change adds a GitHub Actions-only collector prototype for the merged V0.2 preparation comparator. It gathers the pinned contract's source Git blob IDs and an isolated Python runtime manifest. The collector refuses non-Actions execution, a missing isolated-environment attestation, an incomplete distribution inventory, an incomplete source inventory, or a checkout SHA that differs from the freshly obtained main SHA.

The module is not imported by the active weekly training workflow. This change does not modify the workflow, schedule, V0.1 runner or active fingerprint config. It does not read a dataset catalog, shard receipt, latest pointer or R2 object; it makes no provider request, training call or storage write. Dataset identity remains caller supplied and is not authenticated by this prototype.

## Cloud verification

The new test file runs under the repository's GitHub-hosted CI matrix. Synthetic temporary files verify Git blob hashing, exact required-path coverage, stale-main rejection, missing-path rejection, runtime normalization and missing-tool fail-closed behavior. No local project files or local test run are used.

## Follow-up gates

Before wiring any collector into the active workflow, a separate exact-head implementation receipt must pin this collector and the comparator, and the caller must obtain current main SHA through the GitHub API. The expanded import and dynamic-loader closure must include the exact runner, workflow, authority receipt, package initializers and support files. A separate versioned activation authority must define catalog/shard-receipt reads, R2 object scope, training outputs, FREE-ONLY headroom checks, stop conditions and rollback. Until that authority is reviewed and merged, V0.1 remains active and unchanged.

This prototype creates no execution authority. PAPER / LIVE-PAPER ONLY, holdout closed, source switch closed, and the 0 USD/month budget remain binding.
