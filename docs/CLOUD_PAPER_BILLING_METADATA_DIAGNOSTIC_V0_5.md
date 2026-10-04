# Billing metadata diagnostic V0.5 — one-time execution prepared

## Reason

Billing History V0.3 run [37183381165](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37183381165) is consumed and must not be rerun. It made one GET and returned `BILLING_HISTORY_PAGE_METADATA_MISMATCH`, but did not retain a field-level mismatch diagnostic. V0.4 only validated synthetic `page` and `per_page` fields; it did not cover V0.3's `count` versus returned-row length or `total_count` consistency checks.

## Scope and safety

This successor is a single main-only `workflow_dispatch`, with a required false-by-default confirmation input. A dispatch requires `confirm_one_time_read_only=true`, checks exact one-run history, and may issue exactly one GET to the same billing-history endpoint for page 1 / 100 rows. It does not paginate, retry, follow redirects, fall back to another endpoint, or access R2/D1. Any dispatch/attempt, including a failed request, consumes the authority.

The report retains only fixed reason codes, field names, field presence, JSON type labels and booleans. It does not retain response values, result rows, row count, account identity, invoice details, amounts or raw response. Artifact retention is seven days.

## Meaning

`DIAGNOSTIC_COMPLETE` means only that first-page metadata matches the request and returned rows. It is not billing readiness, complete invoice coverage, zero-cost proof or runtime authority. Cost and billing remain `UNKNOWN`; Cloud Paper stays disabled.

## Execution gate

The workflow is prepared but has not been dispatched. Dispatch only after this authority is merged to main and the owner explicitly confirms the one-time read in the workflow input. Never rerun V0.3 or V0.5.
