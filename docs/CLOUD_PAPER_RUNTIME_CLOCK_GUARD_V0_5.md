# Cloud Paper runtime V0.5 — guarded-clock preparation

This successor preserves the existing V0.4 assembly and uses the prepared
shared writer V0.6 guard for Paper admission. It is disabled by default;
constructing or testing it is not execution authority. V0.4 remains unchanged.

Synthetic CI exercises disabled construction, ordinary NO_TRADE, and a
backward clock step after the shared reservation commits. The latter must
stop before provider or R2 activity and retain the prepaid debit and row.
Mocks and SQLite do not establish live D1 behavior or zero cost.

The new composition is not wired to a workflow and does not authorize
provider, R2, D1 or real trading. Cross-call clock integrity, trusted identity,
all-writer admission, account-wide headroom and production acceptance remain
unproven. Existing callers continue using their existing versions.
