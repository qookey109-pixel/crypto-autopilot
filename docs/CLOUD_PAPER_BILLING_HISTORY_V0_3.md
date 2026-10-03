# Billing History V0.3 — bounded read-only successor

V0.1 and V0.2 are consumed; never rerun them. V0.3 reuses the tested optional-total parser from PR #758. It is a separate one-time main-only workflow, requiring distinct owner confirmation before dispatch. Scope: at most ten sequential billing-history GETs, 100 rows/page, 1,000 rows, 1 MiB/response, 20 seconds/request. No retries, redirects, fallback endpoints, R2/D1, provisioning, provider, training or runtime activation.

A validated empty page ends traversal; a short nonempty page does not. Terminal traversal without a provider total does not establish complete history coverage. Supplied totals must reconcile; atomic snapshot and zero-cost conclusions stay unproven. Failure preserves previously accepted redacted rows, counts the attempted request and stops. Raw response, IDs, URLs, descriptions and account identity remain ephemeral. Artifacts last seven days.

Cloud CI covers missing confirmation/rerun blocking before network, optional-total traversal, cap/duplicate stops and partial fetch failure privacy. The 17 parser regressions remain applicable. Dispatch is pending; do not describe prepared CI as external billing evidence.
