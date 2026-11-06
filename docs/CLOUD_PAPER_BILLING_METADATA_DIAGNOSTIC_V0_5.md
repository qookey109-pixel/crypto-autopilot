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

## Provider contract and cost scope — 2026-11-06

Cloudflare's [account billing history API](https://developers.cloudflare.com/api/resources/billing/subresources/history/methods/list/) describes the pagination object and its fields as optional. Thus the V0.5 observation of absent `count` and `total_count` is compatible with the documented response shape; it does not establish malformed provider data. The frozen V0.5 contract still correctly stopped because it required stronger evidence for completeness. A short page, a successful HTTP response or an omitted total is not by itself proof that the full account history has been retrieved. Do not rerun a consumed authority or weaken its historic gate.

Cloudflare's [billable-usage dashboard documentation](https://developers.cloudflare.com/billing/manage/billable-usage/) states that this view covers usage-based overages and excludes fixed subscription fees. Its billing-period summary, even when zero, is not a complete account-cost assertion or a guarantee about future usage. Product usage is billing-cycle based; query time or the latest displayed date must not be substituted for an independently verified usage-through timestamp.

A future evidence producer must independently establish account and subscription scope, all applicable fixed charges, rated metered usage, coverage and freshness, currency, account-wide writer capacity, and conservative projected headroom. An optional or missing field, unverified account scope, or stale measurement leaves the relevant dimension `UNKNOWN` and the execution gate closed. A provider-documented alternative may be assessed only under a new versioned scope; this clarification authorizes no request, new token, provisioning, schedule, or PAPER run. No private billing records, values, or account identifiers are recorded here.
