# Cloud Paper billable-usage successor V0.3

## Why this successor exists

The consumed V0.2 run [36839577708](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36839577708) made one Cloudflare request and returned HTTP 403. Its fixed safe log code contains no response body, so the precise cause remains unconfirmed.

Repository source inspection shows V0.2 called `GET /accounts/{account_id}/billable/usage`, the Cloudflare API's V2 Alpha/Restricted route. Cloudflare separately documents `GET /accounts/{account_id}/billable-usage` for self-serve billable usage, with Billing Read permission; its published launch guidance describes account-wide usage-based products and daily data updates. This makes the route restriction a plausible explanation for the 403, but does not prove that it was the account-specific cause. Do not rotate or replace credentials solely on this hypothesis.

V0.3 is a new successor authority; it does not rerun or alter V0.2. Its versioned contract is [config/cloud_paper_billable_usage_v0_3.json](../config/cloud_paper_billable_usage_v0_3.json).

## Bound execution scope

- Manual `workflow_dispatch` on protected `main`, one workflow run and one attempt.
- One GitHub Actions history request and at most one Cloudflare GET to `/billable-usage`.
- No explicit date parameters: Cloudflare applies the current billing-period boundary. This avoids assuming calendar-month dates match the subscription cycle.
- 20-second request timeout, zero retries, no redirects, no pagination, 1 MiB response cap, 500-row cap.
- One short-retention secret-free report artifact. Account, billing-account, zone identifiers/names and raw response are omitted.
- No R2/D1 access, no external market data, no provider calls, no schedule, no Cloud Paper runtime or authority changes.
- On HTTP error or ambiguous result: preserve the failure and stop. V0.3 may not rerun.

The report can show returned usage-based costs, but it cannot prove zero total project cost: Cloudflare says fixed-fee subscriptions are not part of billable-usage dashboard totals, provider data updates daily, and actual account coverage must be reviewed. Empty rows, absent cost fields, or a zero subtotal remain `UNKNOWN`.

## Synthetic validation

The V0.3 parser tests cover valid and redacted rows, omitted costs, empty responses, invalid billing periods and quantities, mixed currencies, and observation-time validation. These are synthetic contract tests and do not call Cloudflare.

## Official documentation

- [Cloudflare Account Billable Usage V1 API](https://developers.cloudflare.com/api/resources/billing/subresources/usage/methods/paygo/) — route, current billing-period default, Billing Read token scheme, and row fields.
- [Cloudflare Billable Usage API launch note](https://blog.cloudflare.com/billable-usage-api/) — self-serve account scope and daily update cadence.
- [Cloudflare Monitor Billable Usage](https://developers.cloudflare.com/billing/manage/billable-usage/) — usage-based overages only; fixed-fee plans are excluded.

## Execution status

This successor's one-shot authority becomes effective only after its config and workflow merge to protected `main`. No V0.3 dispatch is included in this change. A later successful run would be one account-level usage snapshot only, not proof of full account inventory, every writer, R2/D1 headroom freshness, invoice totals, or zero cost. Continue to keep Cloud Paper disabled until those independent gates pass.
