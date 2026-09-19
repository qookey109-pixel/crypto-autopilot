# GitHub Official MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED OPERATIONS REFERENCE ONLY — NO PROJECT RUNTIME AUTHORITY**

## Candidate

Registry capability: `github_official_mcp`

Reviewed upstream:

`github/github-mcp-server@85598ba6e1256f7ebf4867b95d63b833c4549264`

License: MIT.

## What was verified

This is GitHub's official MCP server. It supports remote and local operation and
covers broad GitHub surfaces including repository reads, issues, pull requests,
Actions, security findings, notifications and repository mutations.

It can authenticate through OAuth or a GitHub token. Those credentials remain
authority-bearing secrets and their GitHub scopes/permissions matter
independently of MCP tool visibility.

## Strong safety primitives

The pinned implementation provides controls that are useful if Crypto Autopilot
ever needs a project-side GitHub agent:

- explicit toolsets;
- explicit individual-tool allowlists;
- explicit tool exclusions;
- a native read-only mode;
- scope filtering;
- optional lockdown mode for reducing exposure to untrusted public-repository
  issue content.

The server documentation states that read-only mode is a strict filter over the
tool inventory: write tools stay disabled even if another configuration asks
for them.

This is materially safer than enabling the default mixed read/write surface.

## Write surface still exists

Without a read-only upper bound, the reviewed source includes tools for actions
such as:

- create/update/delete repository files;
- create repositories and branches;
- create/update issues and comments;
- create/update/merge pull requests and reviews;
- trigger GitHub Actions;
- modify governance/custom properties;
- manage notifications;
- write discussions/projects/labels/gists.

Therefore the candidate remains HIGH risk in the external capability registry.

## Best fit for this project

Crypto Autopilot already uses a controlled GitHub branch → PR → CI → merge
workflow. There is no current technical gap that requires embedding another
GitHub agent runtime into the project itself.

If a future operator/runtime integration genuinely needs GitHub context, the
preferred shape is a narrow read-only surface, for example:

```text
read-only = true
allowed tools/toolsets =
  repository contents / commits
  pull-request reads
  Actions run/job/log reads
```

Mutation should remain outside that adapter and continue through explicitly
authorized project workflows.

## Credentials are a separate boundary

Read-only MCP mode filters tools, but the underlying OAuth/PAT/GitHub App
credential still has its own permissions.

A future deployment should therefore use both:

1. least-privilege GitHub credential permissions; and
2. MCP read-only/tool allowlisting.

One control is not a substitute for the other.

## Lockdown mode is not authorization

The upstream documentation explicitly describes lockdown mode as a best-effort
content filter rather than a security boundary.

It can reduce prompt-injection exposure from public issue content, but it does
not limit what the credential itself can access. Crypto Autopilot must not treat
lockdown as a replacement for repository permissions or read-only mode.

## Decision

**EVALUATED / NOT APPROVED FOR PROJECT RUNTIME INTEGRATION**

Recommended future scope only if a concrete need appears:

`READ_ONLY_REPO_PR_ACTIONS_DIAGNOSTIC_ALLOWLIST`

No duplicate GitHub runtime should be introduced merely because the tool exists.

## Authority

This evaluation grants no:

- GitHub OAuth/PAT/App credential access;
- remote/local MCP runtime;
- repository mutation;
- branch creation or file writes;
- issue/PR write or merge authority;
- workflow trigger/cancel/rerun authority;
- release or governance mutation;
- secret access;
- Strategy Router/portfolio authority;
- holdout/training/model promotion;
- real-money orders or real live trading.
