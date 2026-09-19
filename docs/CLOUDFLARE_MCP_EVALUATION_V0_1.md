# Cloudflare MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED RESEARCH / OPERATIONS REFERENCE ONLY — NO RUNTIME AUTHORITY**

## Candidate

Registry capability: `cloudflare_mcp`

Reviewed upstream:

`cloudflare/mcp-server-cloudflare@db9084730dd45ebb6ac4dd5d3181d189cc96e98d`

License: Apache-2.0.

## What this repository actually contains

The reviewed repository is an official Cloudflare monorepo of multiple
domain-specific remote MCP servers. It is not one narrow read-only tool.

The README also recommends a separate **Code Mode** server from
`cloudflare/mcp`. That is a different repository and is **not covered** by
this pinned evaluation.

The reviewed domain-specific servers include documentation, Workers
observability, Workers builds, Workers bindings, audit logs, Browser Run,
Logpush, AI Gateway, AutoRAG and other Cloudflare product surfaces.

Most account-scoped servers use Cloudflare OAuth or an authorization bearer
token. That authorization is secret-bearing and can expose account resources
according to its scopes.

## Best-fit read-only subset

For Crypto Autopilot, the strongest potential value is operational diagnosis,
not infrastructure mutation.

Useful future candidates include:

- Workers Observability: logs, metrics and field discovery;
- Workers Builds: list builds, inspect a build and read build logs;
- Audit Logs: inspect account change history;
- Documentation: current Cloudflare reference material.

These are useful for debugging deployment/runtime problems while keeping the
trading core independent from the transport.

Even this subset is not activated by this evaluation. A future adapter would
need a narrow tool allowlist and least-privilege Cloudflare authorization.

## Workers Bindings is mixed read/write and stays disabled

The reviewed Workers Bindings server exposes both reads and destructive
mutations, including:

- create/update/delete KV namespaces;
- create/delete R2 buckets;
- create/delete/query D1 databases;
- create/edit/delete Hyperdrive configurations;
- inspect Workers and Worker source.

Because the same server groups read and mutation surfaces, connecting it with a
broad account credential would create substantially more authority than Crypto
Autopilot currently needs.

In particular, an MCP authorization must never silently grant R2 bucket
creation/deletion or other Cloudflare mutation authority merely because the
project already uses R2 through separately governed paths.

## Separation from existing project authority

Crypto Autopilot already has explicit versioned authority for specific R2 and
Cloudflare-related operations. An external MCP server does not inherit those
permissions.

A future read-only operations adapter must preserve these separations:

```text
Cloudflare observability/audit read
    != R2 object read/write authority
    != bucket create/delete authority
    != Worker deployment authority
    != secret-management authority
```

The project rule that Render must not receive R2 credentials also remains
unchanged.

## Hosted and paid surfaces

The repository documents remote Streamable HTTP servers and notes that some
Cloudflare features may require paid Workers plans.

This evaluation does not create a subscription, change a Cloudflare plan, start
a container/browser task, or invoke any hosted MCP endpoint.

## Decision

**EVALUATED / NOT APPROVED FOR RUNTIME INTEGRATION**

Recommended future scope, only if a concrete operational need appears:

`READ_ONLY_OBSERVABILITY_BUILDS_AUDIT_ALLOWLIST`

Do not connect the entire Cloudflare MCP suite. Do not treat the separate Code
Mode repository as evaluated under this receipt.

## Authority

This evaluation grants no:

- Cloudflare OAuth/API-token access;
- MCP runtime or external-network call;
- Code Mode execution;
- Workers deployment/build mutation;
- Workers Binding mutation;
- R2/KV/D1/Hyperdrive mutation;
- Cloudflare plan/billing change;
- secret access;
- strategy or portfolio authority;
- holdout/training/model-promotion authority;
- real-money order or real live trading authority.
