# Open PR Triage — 2026-09-22

Repository `main` is authority and must be resolved live before every merge decision. Evidence basis for this triage version: `09dfb0d79b88dc56f3cb582c91d8091617437ce2` after PR #426 merged. This SHA is historical review context, not a latest-main claim.

This document is navigation only. It grants no merge, close, workflow-dispatch, provider, R2, holdout, source-switch, promotion, deployment, order, or live-trading authority.

Machine-readable companion: `research/status/open-pr-triage-v0-5.json`.

## Current open backlog

The current open backlog is **six Dependabot pull requests only**:

- #329 — Ruff `0.16.0 -> 0.16.7`: patch-level tooling change. Refresh from current `main` and run the full current CI before any merge decision.
- #326 — boto3 `1.43.75 -> 1.43.93`: patch-level SDK change, but current constraints still pin botocore separately. Review SDK pin coupling before rebuilding from current `main`.
- #327 — `actions/cache` `5.1.0 -> 6.1.0`: major action update in the Pionex paper-training workflow. Rebuild the exact update from current `main` and verify cache semantics.
- #328 — `actions/download-artifact` `7.0.0 -> 8.0.1`: major action update in Pionex asset classification. Rebuild from current `main` and verify exact artifact-ID download behavior.
- #330 — `actions/checkout` `6 -> 7`: broad global action change across many workflows, including current critical paths. Do not merge the old branch directly; review the global pin policy and freeze boundaries first.
- #331 — pyarrow `21.0.0 -> 25.0.1`: major runtime/public-contract change. Current `pyproject.toml` still declares `pyarrow>=18,<22`, while the frozen CI constraints pin `pyarrow==21.0.0`. This old PR is not current-main merge-ready.

Suggested review order for lowest-risk current-main rebuild work:

`#329 -> #326 -> #327 -> #328 -> #330 -> #331`

This is review sequencing only, not merge authorization.

## Closed historical references

The architecture-generation and salvage PRs that V0.4 previously listed as active lanes are now closed:

- #336 — closed without merge; superseded by merged #337/#339 work.
- #315 — closed without merge; provenance/governance ideas remain historical salvage only.
- #307 / #306 — closed without merge; rebuild only from current `main` if deliberately revived.
- #302 — closed without merge; immutable diagnosis evidence was already preserved by PR #340.
- #249 / #199 / #168 / #167 / #166 — closed draft-salvage references only.

A non-null GitHub test merge SHA on a closed-unmerged PR is not evidence that the PR merged.

## Dependency review rules

Every dependency PR must be reviewed independently against live `main`.

Patch/minor changes still require current-main CI. Major runtime/action changes additionally require explicit compatibility review of changed contracts, frozen paths, and current action-pin policy. Historical Dependabot CI from old bases is not merge evidence.

No item in this triage is self-authorized to merge or close another PR.
