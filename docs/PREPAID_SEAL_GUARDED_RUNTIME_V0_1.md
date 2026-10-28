# Prepaid seal-guarded runtime V0.1

Status: IMPLEMENTED_DISABLED; production NOT_WIRED / NOT_RUN / NOT_CONFIGURED.

The cloud_runtime_v0_3 factory reuses cloud_runtime_v0_2. It requires the concrete prepaid ledger and checks meter identity, writer, slot and unused admission before applying the seal-guarded store. It does not accept an independent caller-provided ledger. Construction remains disabled by default and does not activate a slot.

Every additional step/tick read goes through the existing freshness and R2 attempted-operation guards. Caps are unchanged. A bad prior result seal retains the new reservation and prevents writes and settlement. Historical settlement recovery remains blocked pending its own fresh workload authority.

Cloud tests use SQLite plus mocked HTTP/S3, exercising shared admission, next-slot NO_TRADE/account continuity, metered reads, tampering, and mismatched bindings. This is engineering evidence only: current account cost/headroom, all-writer cutover, protected finite claims, D1 provisioning and production authority are still required. No frozen receipt, provider scope, schedule, holdout, source switch, promotion or real-money gate changes.
