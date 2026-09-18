# Paper Run Package Artifact Export V0.1

Status date: 2026-09-19

Status: **PREPARED SECONDARY AUDIT EXPORT ONLY / NOT EXECUTION AUTHORITY**

## Purpose

Artifact Export V0.1 turns one already-built and fully verified
Paper Loop Run Package into deterministic files suitable for GitHub Actions
`upload-artifact`.

It does not create a new proof model. It reuses
`verify_paper_loop_run_package()` and fails closed before writing files if the
package cannot be fully reproduced.

## Output

One export directory contains:

- `package.json` — canonical verified Run Package;
- `manifest.json` — package file size/hash and closed authority;
- `SHA256SUMS` — SHA-256 lines for package and manifest;
- `export-receipt.json` — deterministic secondary-export receipt.

The export receipt is evidence that bytes were prepared for upload. It is not a
Checkpoint, Account state, strategy selection or order authority.

## GitHub Actions

The manual-only workflow is:

`.github/workflows/paper-loop-run-package-artifact-v0-1.yml`

It accepts a repository-relative path to a Run Package JSON, re-verifies it,
exports canonical evidence and uploads the output with GitHub
`actions/upload-artifact`.

The workflow does not use exchange credentials, R2 credentials, provider
requests or holdout data.

GitHub Artifact retention controls evidence availability only. Retention does
not change project state or trading authority.

## Authority

Binding V0.1 rules:

- secondary GitHub Artifact export: authorized;
- Artifact as execution authority: false;
- provider access: false;
- R2 access: false;
- replacement holdout access: false;
- account mutation: false;
- automatic execution: false;
- real-money order authority: false;
- real live trading authority: false.

The existing Paper Run Store remains the persistent paper-state path. GitHub
Artifact remains a portable/temporary audit copy.
