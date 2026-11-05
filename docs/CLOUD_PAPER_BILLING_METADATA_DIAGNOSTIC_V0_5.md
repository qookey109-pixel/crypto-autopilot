# Billing metadata diagnostic V0.5 — one-time execution consumed

## Reason

Billing History V0.3 run [37183381165](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37183381165) is consumed and must not be rerun. It made one GET and returned `BILLING_HISTORY_PAGE_METADATA_MISMATCH`, but did not retain a field-level mismatch diagnostic. V0.4 only validated synthetic `page` and `per_page` fields; it did not cover V0.3's `count` versus returned-row length or `total_count` consistency checks.

## Scope and safety

This successor is a single main-only `workflow_dispatch`, with a required false-by-default confirmation input. A dispatch requires `confirm_one_time_read_only=true`, checks exact one-run history, and may issue exactly one GET to the same billing-history endpoint for page 1 / 100 rows. It does not paginate, retry, follow redirects, fall back to another endpoint, or access R2/D1. Any dispatch/attempt, including a failed request, consumes the authority.

The report retains only fixed reason codes, field names, field presence, JSON type labels and booleans. It does not retain response values, result rows, row count, account identity, invoice details, amounts or raw response. Artifact retention is seven days.

## Meaning

`DIAGNOSTIC_COMPLETE` means only that first-page metadata matches the request and returned rows. It is not billing readiness, complete invoice coverage, zero-cost proof or runtime authority. Cost and billing remain `UNKNOWN`; Cloud Paper stays disabled.

## Execution gate

The one-time workflow was dispatched on 2026-11-04 in [run 41841230890](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/41841230890), attempt 1. It returned `REVIEW_REQUIRED / PAGINATION_METADATA_INVALID` after one read-only Cloudflare request. The response reported a different `per_page` from the request, while `count` and `total_count` were absent. See the [versioned result receipt](../research/receipts/2026-11-04-billing-metadata-v0-5-result-v0-1.json) for the evidence and limits. The exact returned page size was not retained; absence of these fields does not establish complete history coverage.

**The V0.5 one-time authority is consumed. Never dispatch it again or rerun V0.3 or V0.5.** Any further external investigation requires its own merged versioned authority. Billing readiness and the zero-cost conclusion remain `UNKNOWN`; Cloud Paper remains disabled.
