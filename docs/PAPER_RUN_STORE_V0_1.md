# Paper Run Store V0.1

Status date: 2026-09-18

Status: **PREPARED PAPER-EVIDENCE PERSISTENCE / NOT EXECUTION AUTHORITY**

## Purpose

Paper Run Store V0.1 provides explicit persistence for deterministic paper
state and audit evidence.

It is intentionally separate from trading logic.

The first supported object classes include:

- `live-state`;
- `live-tick`;
- `live-run`;
- `live-run-step`;
- `live-run-result`;
- Paper Loop Run Packages;
- other deterministic paper evidence with an explicit object id.

## Content-addressed behavior

Every stored object has:

```text
kind + object_id + canonical JSON payload
```

If the same object id already exists:

- identical bytes → idempotent replay;
- different bytes → collision error.

V0.1 never silently overwrites different evidence under the same id.

## Local JSON backend

`LocalPaperRunStore` requires an explicit absolute root.

There is no repository-directory default.

Writes use a temporary file followed by atomic `os.replace`.

This backend intentionally relaxes the old "ephemeral output only" rule only
for this explicit, versioned paper-state store. It does not change historical
dataset-output rules.

## Cloudflare R2 backend

`R2PaperRunStore` reuses the existing
`crypto_autopilot.storage.r2.R2Store`.

Default object layout:

```text
paper-run-store/v0.1/<kind>/<object_id>.json
```

Credentials remain outside Git and are supplied only by environment / secret
manager.

The existing R2 adapter already verifies SHA metadata on read when available.

## GitHub Artifact

GitHub Artifact is permitted as a **secondary export**, not an authority source.

Paper Run Store itself still does not implement a generic Artifact storage
backend. A separate versioned layer,
`Paper Run Package Artifact Export V0.1`, now verifies one Run Package and
provides a manual GitHub Actions `upload-artifact` path for secondary audit
copies.

The separation is intentional:

```text
GitHub Artifact != account authority
GitHub Artifact != execution authority
```

R2 / explicit local content-addressed state remain the actual persistence
backends implemented in V0.1.

## Storage does not grant execution

Persisting an object never changes its authority.

Binding rule:

```text
stored_object_becomes_execution_authority = false
```

Paper state saved in R2 therefore cannot authorize:

- strategy promotion;
- real-money order placement;
- private exchange API use;
- live real trading.

## Security

Run Store objects must not contain:

- API secrets;
- private keys;
- R2 secret keys;
- exchange account credentials.

R2 credentials are used only to construct the existing storage adapter and are
not serialized into receipts.

## Authority

Paper Run Store V0.1 authorizes persistence of paper evidence through explicit
Local JSON and Cloudflare R2 backends.

It grants no market-provider authority, holdout access, real-money order
authority or live-real-trading authority.
