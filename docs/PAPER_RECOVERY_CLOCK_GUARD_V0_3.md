# Prepared clock-guarded recovery V0.3

The disabled successors for Live-Paper and Cloud-Paper result-seal recovery
use the prepared V0.6 shared writer guard. The new scoped core reuses the
existing seal-only stores and reconciliation function, preserving separate
namespaces, immutable seal checks and bounded listing. Older versions remain
unchanged; no workflow or cloud resource is changed.

Synthetic tests use SQLite and mocked storage to exercise repair, duplicate
admission and a clock step backward after the reservation commits. This is not
proof of live Cloudflare transaction semantics, account-wide admission,
trusted cross-call time or namespace ownership. No production access, repair,
schedule, provider operation, holdout, promotion or trading is authorized.
