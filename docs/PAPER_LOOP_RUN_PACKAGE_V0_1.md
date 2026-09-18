# Paper Loop Run Package / Transcript V0.1

Status date: 2026-09-18

Status: **PREPARED PORTABLE-AUDIT-PACKAGE-ONLY / NO EXECUTION AUTHORITY**

## Purpose

Paper Loop Run Package V0.1 bundles one already-audited multi-cycle paper
transcript into a single deterministic, self-verifying JSON handoff.

It packages:

- the complete Paper Loop Integrity input transcript;
- the complete Integrity PASS report;
- a per-round, per-stage SHA-256 manifest;
- the terminal Checkpoint needed for any future explicit Resume.

The package itself performs no trading, no simulation and no persistence.

## Position in the architecture

The execution chain ends at Checkpoint / Resume.

Run Package is an **audit sidecar**:

```text
completed paper-loop rounds
        ↓
Paper Loop Integrity / Multi-Cycle Replay
        ↓
Paper Loop Run Package / Transcript
```

It is not inserted into the order path and is not required to submit, fill or
advance a paper position.

## Double verification

Before packaging, V0.1:

1. validates and recomputes the supplied Integrity report id;
2. requires exact Integrity-id confirmation;
3. parses the complete Integrity input transcript;
4. re-runs Paper Loop Integrity over that transcript;
5. requires the re-audited report to exactly equal the supplied proof.

Only then is the package created.

## Stage manifest

For every forward round, the package records six canonical stages:

1. start Checkpoint;
2. Resume report;
3. Submission Session report;
4. Lifecycle Batch report;
5. Account Advance report;
6. end Checkpoint.

Each manifest row includes:

- deterministic stage id;
- SHA-256 of the complete stage payload;
- SHA-256 of the complete round payload.

The package also binds a SHA-256 of the complete manifest.

## Deterministic package id

The package id binds:

- Integrity id;
- SHA-256 of complete Integrity input;
- SHA-256 of complete Integrity report;
- SHA-256 of complete stage manifest;
- terminal Checkpoint id.

The same verified transcript and proof therefore produce the same package id.

## Full self-verification

`verify_paper_loop_run_package()` independently:

- re-runs Integrity;
- validates the Integrity report id;
- rebuilds the stage manifest;
- rechecks all transcript/proof/manifest hashes;
- rechecks the embedded terminal Checkpoint;
- rechecks closed authority flags;
- recomputes the deterministic package id.

No network access is needed.

## Terminal Checkpoint

The package includes the exact terminal Checkpoint payload.

That makes the package useful as an audit handoff, but it does **not** authorize
another cycle.

A future cycle still requires explicit Paper Loop Resume with the Checkpoint's
exact id.

## CLI

```bash
PYTHONPATH=src python scripts/build_paper_loop_run_package_v0_1.py \
  --input /tmp/paper-loop-run-package-input.json \
  --confirm-integrity-id paper-loop-integrity-v0-1-...
```

Input shape:

```json
{
  "schema": "qookey-paper-loop-run-package-input-v0.1",
  "integrity_input": {},
  "integrity_report": {}
}
```

The CLI writes only JSON to stdout.

It does not create a repository artifact, local state file, R2 object, database
row or PaperBroker state.

## Naming boundary

This package is intentionally different from historical V0.11
**execution-package** governance files.

Paper Loop Run Package V0.1 is:

```text
portable audit transcript package
```

It is **not**:

```text
execution authority
```

The machine-readable authority field
`package_is_execution_authority=false` is binding.

## Explicit non-goals

V0.1 does not:

- generate candidates;
- Resume a Checkpoint;
- submit paper orders;
- simulate lifecycle bars;
- advance account state;
- persist package data;
- upload GitHub artifacts;
- access providers;
- access R2 or replacement holdout;
- rank strategies;
- authorize formal trade plans;
- place real-money orders;
- enable live trading.

## Authority

Paper Loop Run Package V0.1 authorizes only deterministic in-memory/stdout
packaging of already-audited paper evidence.

It grants no provider access, R2 access, holdout access, persistent state write,
automatic execution, automatic submission, strategy-ranking authority,
real-money order authority or live-trading authority.
