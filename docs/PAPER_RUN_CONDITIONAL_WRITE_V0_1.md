# Paper Run Conditional Write V0.1

Status date: 2026-09-19

Status: **PREPARED STORAGE PRIMITIVE ONLY / NOT WIRED INTO COORDINATOR**

## Purpose

Live Paper Run Recovery V0.1 can detect a fork after persisted evidence exists.
The next safety problem is preventing two workers from winning the same future
coordination slot in the first place.

This version does **not** yet add a lease, takeover protocol or Coordinator
behavior change. It adds only the storage primitive needed by a future
transactional claim layer:

> create one paper-run object only if the exact object key does not already
> exist.

An existing key is a hard conflict and is never interpreted as a successful
replay by this layer.

## Local semantics

`LocalPaperRunStore.put_json_if_absent()` uses exclusive file creation.

That gives one-writer create semantics on the local filesystem for the exact
destination path. A pre-existing path raises
`PaperRunObjectAlreadyExistsError`.

## Cloudflare R2 semantics

`R2PaperRunStore.put_json_if_absent()` uses the existing R2 S3-compatible
client with:

```text
If-None-Match: *
```

Cloudflare R2 documents conditional `PutObject` support, including
`If-None-Match`. A failed precondition is mapped to
`PaperRunObjectAlreadyExistsError`.

The frozen generic `src/crypto_autopilot/storage/r2.py` adapter is not
modified. The conditional behavior remains scoped to Paper Run Store.

## Why this is not a lease yet

A safe lease needs more than one atomic create. It needs reviewed semantics for
ownership, crash handling, expiry or supersession, and stale-writer rejection.

V0.1 intentionally does not invent those rules.

Therefore:

- no Coordinator call site uses this primitive yet;
- no existing Live Paper request changes behavior;
- no automatic retry is inferred from a conflict;
- no claim can grant provider or trading authority;
- no workflow or schedule is added.

## Intended next step

A later Live Paper Run Claim / Lease layer may bind a deterministic run slot to
one explicit request and use this primitive to reject concurrent writers before
any provider call.

That integration must separately define what happens when the winning worker
crashes before a committed step exists. Until then, this module is capability
proof only.

## Authority

Authorized by this version:

- local atomic create-if-absent;
- R2 conditional create-if-absent within Paper Run Store;
- unit/regression verification of those semantics.

Not authorized:

- Coordinator integration;
- automatic retry or lease takeover;
- provider access;
- live market-data access;
- account/state mutation;
- automatic scheduling;
- private exchange APIs;
- replacement holdout;
- real-money orders;
- real live trading.
