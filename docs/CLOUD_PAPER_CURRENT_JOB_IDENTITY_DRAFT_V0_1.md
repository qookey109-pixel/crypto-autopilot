# Cloud Paper current-job identity — decision record (draft)

Status: **NOT IMPLEMENTED / NO EXECUTION AUTHORITY**. This document belongs to
a draft PR. The existing prototype compares caller-supplied IDs and does not
establish that its caller is the GitHub job whose ID it uses. Do not merge or
use it as an authentication boundary.

## Concrete failure

The prepaid ticket controller retrieves an in-progress run by a supplied run
ID, verifies metadata and creates a protected tag that points to main. A caller
able to reach that transport can supply a different qualifying run ID; the tag
does not itself identify its owner. Python private names, frozen dataclasses and
`GITHUB_RUN_ID` environment variables are not proof of current job identity.

## Proposed verification chain

1. A separately approved successor defines exact issuer, audience, repository
   immutable ID and name, workflow path and approved commit, branch, events,
   run attempt, job/check ID, time bounds, and a finite run/slot scope.
2. GitHub documents `check_run_id`, `run_id`, `run_attempt`, `workflow_ref`,
   `workflow_sha`, `ref_type` and `runner_environment` as claims; its docs also
   emphasize validating `sub` and `aud` together. Validate the exact subject
   format and hosted-runner condition against the eventual reviewed authority;
   do not infer a privileged job merely from the workflow or a caller-provided
   expected value. Reusable-workflow claims are conditional and must not be
   assumed in a normal workflow.\n\n   Verify a GitHub-signed job identity with a maintained cryptographic library.
   Reject algorithm confusion, unrecognized key ID, wrong signature, missing or
   duplicated claims, wrong issuer/audience/repository/workflow/commit/ref/event,
   invalid time bounds and unexpected attempt. Never print or persist tokens.
   GitHub's documented claims are listed in
   https://docs.github.com/en/actions/reference/security/oidc .
3. The verifier must obtain keys through a bounded, authenticated trust path
   pinned to GitHub's issuer, with a documented rotation and failure policy.
   Neither a caller-provided signing key nor a caller-provided expected audience
   establishes trust. An offline synthetic key proves implementation behavior
   only; it is not a production key.
4. Cross-check signed run and job/check identities with GitHub metadata and
   protected main. Derive the Paper run ID from verified evidence rather than
   accepting the caller's value. Slot is not a signed GitHub OIDC claim; bind
   its canonical schedule and timestamp separately to the run and trusted clock.
5. A bearer token may be replayed or stolen. A durable atomic claim must prevent
   a second token from the same job/attempt/writer/slot, survive crashes and
   concurrent attempts, and preserve ambiguous results. A token's jti alone is
   insufficient because a job may request multiple tokens. Protect that claim
   from update, deletion and bypass. Document the residual compromised-runner
   threat and do not treat Python access controls as a sandbox.
6. Bind the verified claim to the sole protected production entrypoint, query
   meter, D1 account/database, R2 bucket, slot and clock. Earlier prepared
   factories remain callable Python code and are not automatically secured by
   a wrapper. Unknown identity or bypassable entry stops before D1/R2/provider.

## Required independent enforcement boundary

The OIDC JWT is a bearer assertion. A signature establishes who issued an
assertion and what it says, not that arbitrary Python code submitting it is the
job named in it. Local verification plus private attributes cannot prevent a
copied token or another callable gateway from spending. A production successor
therefore needs an independently enforced credential boundary: the component
holding D1/R2 credentials must validate the signed identity, bind its accepted
job and slot, and atomically consume a protected claim before releasing a bounded
operation. The authorized workflow and every other writer must be unable to
bypass that component with the same credentials. A stolen token can still win
a race; that residual risk must be included in the threat model.

The SQLite experiment in this draft has no such independent boundary and is not
an implementation of this requirement. The existing GitHub ticket reference
points to a commit rather than an authenticated job; it also cannot by itself
attest that an object writer lacks another credential. No proposed identity
adapter may activate until the credential inventory, sole entrypoint, protected
claim semantics, operation budget and failure/readback behavior have all been
verified under a merged successor. OIDC only verifies a signed bearer; it is not
a trusted-clock, slot, account-headroom or source-integrity proof.

## Validation and authority frontier

- Cloud CI only: synthetic RSA signatures, fake GitHub responses and controlled
  clock; no live OIDC request or workflow permission change. Cover wrong key,
  altered signature, algorithm/kid confusion, wrong identity/claims, expiration,
  time skew, replay, concurrent duplicate claims and late/partial failure.
- Test full V0.5 PAPER composition, duplicate slot and failure recovery with
  no real provider/D1/R2 access. Verify mismatch causes zero downstream access.
- A later live successor needs new versioned authority on protected main for
  token issuance, discovery/JWKS, run/job metadata, claim/readback, request
  bounds, trusted code and runner. Recompute all API attempts, key refreshes and
  runner usage; the existing eight-request ticket ceiling cannot be assumed to
  cover additional calls. Verify FREE-ONLY account headroom independently.
- CI does not prove real GitHub signing-key retrieval, ruleset enforcement,
  runner identity, token confidentiality or replay protection. D1 atomicity,
  Cloudflare cost/headroom and all-writer coverage remain separately unproven.
- No new workflow, OIDC permission, GitHub claim, Cloudflare operation, data
  source, holdout, source switch, promotion or trading authority is created by
  this record.
