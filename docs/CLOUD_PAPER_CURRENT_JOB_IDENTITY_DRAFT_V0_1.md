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

## Direct credential paths observed on main

On main `ae9faa2032af6f2d2b5cfc14123b7229b992d2d2`, static workflow
inspection found direct R2 credential injection outside the proposed broker.
This is a capability and migration inventory, not evidence that a given run
actually accessed R2 or that all account users and secret aliases are known.
The following paths must be independently classified and their active authority
and actual read/write operations verified before any sole-gateway claim:

- `.github/workflows/research-signal-layer-v0-2.yml`: scheduled and manually
  dispatched research publication explicitly invokes `--publish-r2`.
- `.github/workflows/research-signal-quality-v0-1.yml`: scheduled,
  workflow-run and manual quality check declares R2 writes forbidden but reads
  evidence; reads also consume shared account resources and must be budgeted.
- `.github/workflows/binance-usdm-detailed-training-v0-1.yml`: scheduled
  fingerprint comparison and manual execution receive R2 credentials; current
  runtime guards and consumed bootstrap prevent assuming new training or writes.
- `.github/workflows/live-paper-run-coordinator-v0-1.yml` and
  `.github/workflows/live-paper-run-recovery-v0-1.yml`: manual paths receive
  the same credential names; recovery exposes an optional repair mode. They
  cannot be assumed to share the new broker's admission or replay claim.
- Spot training/monthly governance, historical repair, Pionex pilot and
  materialization, forward context capture, alternative-assets observability,
  and provider-equivalence capture workflows also contain direct secret bindings.
  Some are historically constrained, retired, read-only or past their fixed
  windows; secret binding alone does not establish current execution authority.

A read-only Cloudflare R2 token-list observation on 2026-11-05 showed at least
one active account token scoped to the project bucket with object read/write,
and two active user tokens with administrator read/write across all buckets.
The observation does not identify which token supplies the GitHub secret, who
holds each credential, whether other services use it, or whether the visible
list covers every account access method. It is not proof of shared-budget
admission, actual usage, a zero-cost guarantee, or a reason to revoke a token.
No token values or account identifiers are recorded here.

The repository secret scope and provider-side key privileges have not been
verified by this static review. A safe cutover needs verified least-privilege
credential separation, inventory of external and future users, read and write
budgets, treatment of retired workflows, and evidence that no legacy path can
use the broker's protected credential. Do not revoke existing credentials or
change historical workflows solely on this inventory.

## Cloudflare Worker candidate: constraints, not a selected deployment

A Worker holding D1/R2 bindings is one possible independent enforcement
boundary, subject to a separate reviewed successor and complete inventory of
existing credentials. This is a design candidate, not an enabled service and not
evidence that existing direct credentials have been removed.

Cloudflare's current [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
list 100,000 daily requests at the account level, 10 ms CPU per request on
Workers Free and bounded subrequests. Other projects share the account budget.
JWT verification and any key-fetch or storage work must be measured within
these constraints; do not assume a cache hit, free capacity, or successful
execution. For security-critical routes the documented fail-closed behavior
must be established rather than relying on a route that bypasses the Worker.

Cloudflare's [D1 free-tier enforcement](https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/)
states that daily row-read/write overages cause queries to fail, including
binding and REST access. This does not establish the account plan, current
usage, remaining R2 capacity, or zero projected fees. Any D1-backed replay claim
also consumes queries and rows, so an independently bounded bootstrap/admission
budget and ambiguous-commit handling are required before deployment. Paid-plan
behavior, direct legacy writers and all other account activity must be included
in the account-wide evidence; no paid fallback is authorized.

## Runtime compatibility discovered 2026-11-05

The current candidate verifier and key loader are CPython runner code; they are
not a Cloudflare Worker implementation. The existing prepaid controller uses
`threading.Lock`, while [Cloudflare's Python Worker standard-library limits](https://developers.cloudflare.com/workers/languages/python/stdlib/)
say `threading` is nonfunctional in that runtime. CPython CI cannot establish
Worker package, networking, concurrency, Web Crypto or D1 binding behavior. In
particular, do not deploy or wire this controller in a Python Worker unchanged.

An independent Worker boundary would need a Worker-native asynchronous transport
and cryptographic verification, durable atomic claim and budget admission via
supported bindings, and a separately reviewed credential migration for *all*
relevant readers and writers. [D1 batch documentation](https://developers.cloudflare.com/d1/worker-api/d1-database/)
describes transactional batches, but [D1 accounting](https://developers.cloudflare.com/d1/observability/find-expensive-queries/)
still counts individual statements and their rows. Neither statement proves
that this account has enough headroom or that an ambiguous response is safe to
replay. A design that bypasses these boundaries must stay disabled.

## Worker-native identity prototype

This draft contains a Web Crypto RS256 verifier and a fixed GitHub JWKS reader.
The verifier is disabled by default, rejects duplicate JSON keys and unrecognized
headers, checks signed claims, and treats the optional documented `x5t` header
as metadata rather than as a trust source. The reader is disabled by default,
pins the issuer's published JWKS URL, refuses redirects, bounds response bytes,
and makes no retry. Tests use generated signing keys and a fake fetcher.

The draft also contains a bounded, no-redirect GitHub metadata reader and a
comparison of the signed run/check identifiers, repository, event, workflow,
commit, attempt, job, status and time. Only fixture responses have been used.
The comparison does not prove that a job is still active when a later operation
runs, that a bearer has not been copied, or that an unsigned slot belongs to
the run. Policy, token and endpoints must be server-owned, never supplied by a
request. The proposed two metadata GETs plus JWKS GET and all retry/overhead
must be reserved separately; none is covered by the existing ticket ceiling.

These are separate synthetic primitives, not an independent gateway. The
verifier currently accepts a caller-provided policy, time and key callback;
a future deployment must instead enforce server-owned values and protect the
whole credential boundary. The code has not established Worker-runtime
compatibility in Cloudflare, key rotation, job metadata cross-checks, atomic
slot/replay claims, budget admission or all-writer coverage. A successful Node
test is not a live GitHub OIDC or Cloudflare validation. No bearer token,
production service or paid capability is used by this prototype.

## Synthetic admission composition

The draft composes the verifier, fixed key reader, bounded metadata reader,
metadata comparison and D1 claim using fake credentials and an in-memory
database in cloud CI. Its injected reservation is a fixture, not a real shared
budget; it is not a Worker request handler and must never receive production
bindings. A green composition test proves only the tested sequencing.

The test computes a candidate quarter-hour slot from run creation time. GitHub
does not sign the nominal scheduled slot in OIDC, and a delayed run may have a
creation timestamp close to a later nominal slot. Therefore the calculation
cannot prove slot identity, even with a three-minute window. It must not be
used to authorize production. A successor needs a separately verified slot
assignment or must fail closed when the slot cannot be established. Manual
controlled acceptance is also not implemented in the synthetic composition.

## Prepared D1 claim adapter and retry accounting

The draft Worker adapter issues one parameterized insert and accepts only an
unambiguous single-attempt D1 success; duplicate constraints stop progression,
and an exception or uncertain metadata returns `REVIEW_REQUIRED`. The table
schema is a synthetic test fixture only. Node's in-memory SQLite test is not
evidence of actual D1 concurrency, D1 schema deployment, isolated credentials,
a prepaid claim or a valid policy. The adapter must not receive caller-chosen
job IDs or slot IDs in a deployed route, and its enabled flag is not authority.

Cloudflare documents that [D1 read-only queries may be retried automatically
up to twice](https://developers.cloudflare.com/d1/best-practices/retry-queries/).
Any Worker binding successor must budget up to three attempts for each such read,
including admission and readback, and must treat missing or unexpected
`meta.total_attempts` as unknown rather than assuming one request. The claim
adapter itself performs a write and does not perform application retries. This
observation does not prove retry behavior of the existing REST path, account
allowance, or actual usage; each transport needs its own verified accounting.

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
