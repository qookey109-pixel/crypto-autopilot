# Prepaid recovery D1 V0.2

Status: PREPARED_DISABLED. This successor whitelists only the conservative
V0.5 shared reservation and replay-read statements for the Live-Paper and
Cloud Paper result-seal recovery writers. It binds the writer, canonical current
slot, full prepaid D1 envelope and fixed recovery workload (zero provider calls,
8 Class A, 64 Class B, 16384 new bytes). It validates freshness before and
after each statement, retains debits on failures, and poisons ambiguous
responses instead of retrying.

Cloud CI uses in-memory SQLite and synthetic prepaid tickets. It does not
verify production D1 concurrency, all-writer coverage, account headroom,
authenticated job identity, namespace ownership or actual request costs.
This client is not yet connected to the recovery assembly, workflow, a live
database or a schedule. An enabled flag is not authority. Future integration
requires the exact reviewed successor, verified policy, independent credential
boundary, all-writer admission and a separate finite execution authority.

The V0.1 recovery paths and their existing contracts remain in place.
No frozen receipt, existing workflow or account resource is changed here.
