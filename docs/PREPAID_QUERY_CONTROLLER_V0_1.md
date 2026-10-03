# Prepaid Admission Query Controller V0.1

## Implemented, disabled

V0.4 now has a concrete query-meter factory and a GitHub REST claim backend.
The runtime remains unwired. The merged default configuration disables claims
before any request. No production tag, ruleset, D1 database, or schedule is
created by this implementation.

The controller uses GitHub as an independent finite ticket ledger because
a D1 query cannot safely fund its own admission query. This keeps account,
strategy, workload reservation and persistence contracts separate. Existing
frozen V0.3/V0.4 contracts are preserved.

## How the prepaid bound works

1. A merged finite authority defines one immutable scope (at most 31 days),
   approved writer/workflow identities, daily ticket counts, query counts, and
   calibrated per-statement D1 read/write/storage ceilings.
2. Reserve the **entire daily ticket pool across all writers** against fresh
   account-wide remaining headroom. Other workloads, prior scopes, unreflected
   usage, and control overhead must already be subtracted. Pre-fund cumulative
   storage for every day in the scope. Repository flags alone are not evidence.
3. Resolve live main, reread this exact authority from that SHA, and authenticate
   the run via GitHub metadata. Only attempt 1 of an in-progress main
   schedule/dispatch on the approved workflow may claim. Delayed runs stop.
4. Verify an active exact-scope tag ruleset with update/deletion restrictions
   and **no bypass actors**. The current repository has only main branch
   protection; it does not yet have this claim protection.
5. Derive one ticket from the verified workflow run number modulo that writer's
   daily allocation. Atomically create its lightweight tag pointing to main.
   An existing ticket or any rejection stops; never search a second ticket.
6. Read the exact ref back, recheck protection and main. Only then create a
   meter and connect it to V0.4 admission through
   `claim_and_reserve_shared_writer_envelope`.
7. Debit the in-process query count before every SQL attempt. The full remote
   envelope has already been burned, including unused allowance. A crash,
   rejected SQL or ambiguous response never refunds it. A fresh process must
   claim again, finds the existing tag and stops before D1.
8. UTC rollover or expired account evidence stops before the next SQL.
   Replaying an old workload slot charges the current ticket day.

For metric `m`, writer `w` and approved operation `o`:

`ticket[w,m] = queries_per_ticket[w] * max(statement_cost[o,m])`

`daily_pool[m] = sum(daily_tickets[w] * ticket[w,m])`

Storage uses `daily_pool[storage] * scope_day_count`. Conservative overlap with
the workload ledger is allowed; silent netting/refunds are not.

Tickets are partitioned by writer but their total is bounded by one account
allocation. Future services need registration and an allocation before writing.
The finite ring can reject surplus runs or a collision. This sacrifices some
availability to retain the cost bound; the rejection must remain visible.

## Costs and security

A successful claim makes exactly eight GitHub requests: main, authority, run,
protection, create, readback, protection, main. Failed paths make fewer requests.
Each transport has one attempt, a ten-second timeout and bounded response body;
redirects and automatic retries are disabled. HTTP errors retain only the status
code. A 422 is not automatically classified as a replay because GitHub also uses
it for invalid or throttled requests. No raw response, token or account identity
is recorded.

This controller itself performs **zero D1/R2/Cloudflare requests**. GitHub API
rate limits, Actions minutes and any generated artifacts still need a project
usage envelope. Failed claim attempts can hit GitHub rate limits and must stop.
No account fee conclusion follows from this implementation.

The eventual trusted gateway needs contents-write for the exact tag create
endpoint plus read access to main/run/ruleset. Claim tags must not be updated or
deleted. Ruleset creation, activation, and credentials are separate deployment
steps; this PR does not modify repository settings or bind a new secret. Do not
modify main protection or add a bypass to make claims succeed. Tag creation
restrictions that prevent creation result in a safe rejection.

The controller class rejects direct construction without its private factory
confirmation. This is an accidental-misuse guard, not a sandbox against
malicious Python code or repository administrators. Production trust rests on
reviewed main code, the protected claim namespace, and the governed gateway.
Administrative removal of protection is an incident requiring suspension.

## Validation and remaining integration

Cloud CI exercises successful and rejected claims, independent reconstructed
callers, concurrent callers, lost create responses, changed main, missing or
bypassed protection, bounded query debits, writer allocations, full-scope storage,
UTC/evidence expiry, disabled configuration, HTTP redaction and one transport
attempt. The composition test uses the **actual V0.4 SQL** on SQLite and confirms
a fresh controller cannot issue a second SQL after the claim is burned.

The remote service is simulated in CI. These tests do **not** prove GitHub tag
protection behavior under production credentials, Cloudflare D1 transaction or
meta cost bounds, current account completeness, or an operating Cloud Paper
loop. Live acceptance needs a separately merged activation authority and finite
account evidence. No-op callbacks and caller-provided unsupported cost estimates
remain unsuitable for production.

The next product work is to provide the account evidence and bounded gateway
wiring, configure and verify claim protection under authority, and execute
controlled PAPER acceptance. Empty qualified strategy registry is a valid
`NO_TRADE` outcome and does not require promoting the rejected Core100 model.

Official interface references:
[Git references](https://docs.github.com/en/rest/git/refs) and
[Repository rulesets](https://docs.github.com/en/rest/repos/rules).

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY.
Holdout, source switch, promotion, real orders and live trading stay closed.
