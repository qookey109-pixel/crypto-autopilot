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
2. Verify a GitHub-signed job identity with a maintained cryptographic library.
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
