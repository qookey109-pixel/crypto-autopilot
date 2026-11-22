# Shared writer budget V0.6 — monotonic clock preparation

This is a disabled synthetic successor, not production activation or a new
Cloudflare access authority. V0.5's reservation SQL, schema, policy and historical
evidence remain unchanged.

On the V0.5 implementation, PR #926 head `1d06c5cf10ced4cc882bfc2a1ce61a320235ae8f`
produced a failing synthetic regression: after a committed insert, a backwards
clock step that remained inside the nominal window did not raise BudgetBlocked.
See [CI run 44990332583](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/44990332583).

V0.6 wraps the existing function with a per-call nondecreasing clock check.
If the clock steps backward after a ledger commit, it blocks release and the
committed reservation and prepaid debit remain consumed. A step backward after
debit but before SQL blocks the query and retains the debit. The wrapper is
disabled by default; its clock must still be protected and trusted by the eventual
runtime. It cannot detect a backward step between separate calls or a clock
that moves slowly while remaining monotonic.

This does not wire existing workflows to V0.6. Independent identity, all-writer
admission, calibrated D1 costs, persistent time assurance, account headroom,
and a versioned execution authority remain unproven. No Cloudflare, D1, R2,
provider or trading operation is authorized.
