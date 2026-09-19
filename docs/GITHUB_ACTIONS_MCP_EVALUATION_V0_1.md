# GitHub Actions MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED / REDUNDANT / NOT SELECTED FOR INTEGRATION**

## Candidate

Registry capability: `github_actions_mcp`

Reviewed upstream:

`devopsier/github-actions-mcp@b13a4df3d3feedf123d3b53f21c4a739f5ab4907`

Pinned commit date: 2025-04-20.

## Reviewed surface

The pinned server registers a small GitHub/Actions tool surface:

- list repositories;
- list/get workflows;
- get repository details;
- trigger a workflow;
- list workflow runs;
- retrieve run logs;
- cancel a workflow run.

The underlying client also contains additional workflow mutation methods such as
rerun/delete run and delete logs, even though they are not all registered as MCP
tools at the pinned commit.

Runtime requires a GitHub token.

## No native read-only upper bound was found

Unlike the evaluated official GitHub MCP server, this pinned implementation does
not provide an equivalent native read-only mode, composable toolset filtering,
individual-tool allowlisting or explicit tool-exclusion system.

Its registered MCP surface already mixes reads with:

- workflow dispatch;
- workflow-run cancellation.

Therefore a future consumer would have to wrap or modify the server itself to
obtain a trustworthy read-only surface.

## Functional overlap

The official `github/github-mcp-server` candidate already provides GitHub
Actions read/diagnostic tooling together with:

- native read-only mode;
- tool/toolset filtering;
- scope filtering;
- broader maintenance and security activity.

For Crypto Autopilot, this third-party candidate does not add enough unique
capability to justify a second GitHub token-bearing runtime.

## License metadata inconsistency

The pinned repository's `package.json` declares:

`license = ISC`

The README says the project is MIT-licensed and refers to a LICENSE file, while
the reviewed repository root does not expose that LICENSE file and GitHub's
repository license field is unset.

The registry therefore keeps its existing package-metadata evidence, but this
evaluation treats the licensing presentation as inconsistent rather than
silently rewriting it to MIT.

No upstream source is copied into Crypto Autopilot.

## Decision

**EVALUATED / DO NOT INTEGRATE**

Reason:

`REDUNDANT_WITH_OFFICIAL_GITHUB_MCP_AND_WEAKER_PERMISSION_NARROWING`

This is a convergence decision, not a claim that the upstream project is unsafe
or unusable in general.

If GitHub Actions MCP capability is ever needed inside Crypto Autopilot, prefer
a narrowly configured **official GitHub MCP read-only Actions surface** instead
of introducing this additional runtime.

## Authority

This evaluation grants no:

- GitHub token use;
- MCP runtime;
- workflow dispatch/cancel/rerun/delete;
- repository mutation;
- external network access;
- secret access;
- Strategy Router/portfolio authority;
- holdout/training/model promotion;
- real-money orders or real live trading.
