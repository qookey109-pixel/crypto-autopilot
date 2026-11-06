# Shared-admitted Live-Paper coordinator V0.1

This is a disabled-by-default Python composition for the existing manual Live-Paper writer. It uses the fixed registered writer ID and V0.5 prepaid D1 admission, reserves the entire conservative Paper per-run envelope before constructing an R2 store, meters each actual R2 and public Pionex request, and checks target, clock, usage and prepaid evidence again before later operations.

The first invocation requires a new run identity. An existing run requires an explicit prior step, complete bounded run reconciliation, a consistent terminal result seal, and matching lineage before a new step. A missing seal, incomplete scan, conflict, late evidence or ambiguous write yields `REVIEW_REQUIRED` and retains the reservation; no automatic retry or partial repair occurs. A duplicate central reservation blocks before R2/provider access. Inventory growth may exhaust bounded scan or operation budgets and then stops safely; it is not a proven indefinitely scalable recovery scheme.

Synthetic tests exercise no-trade, a fixture Paper session, admission, duplicate, next-slot continuation and missing-result refusal. These are not strategy validation or real Cloudflare usage. The legacy workflow has **not** been switched to this composition; other repository writers still lack verified shared admission. The meter and callback are not authenticated caller boundaries. Fresh account coverage, calibrated statement costs, exclusive namespace ownership, independent caller identity and a separately merged finite execution authority remain prerequisites for any production operation.

No workflow, schedule, D1 provisioning, provider call, real-money trading, holdout, source switch or promotion is authorized by this preparation.
