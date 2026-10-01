# Cloud Paper billable-usage diagnostic V0.2

## Authority and purpose

The versioned execution contract is config/cloud_paper_billable_usage_v0_2.json. Once merged to protected main, the manual workflow is authorized for exactly one first-attempt run: one GitHub Actions workflow-history request and at most one Cloudflare request. Run only from main. The workflow has no retry, pagination, redirect following, fallback endpoint, or rerun permission.

The request covers the current UTC calendar month through the current UTC date, with an explicit date range no longer than 31 days. It uses repository variable CLOUDFLARE_ACCOUNT_ID and repository secret CLOUDFLARE_BILLING_READONLY_API_TOKEN. It prints neither value and does not persist account identifiers or the raw response.

## Interpretation

The API describes daily account billable-metric usage, including metered usage within free-tier allowances. Returned rows can help identify reported metric quantities and period boundaries. The diagnostic keeps only metric ID, charge period, consumed quantity/unit, and any returned billed cost/currency.

A well-formed nonempty response is READY_FOR_REVIEW, not a cost pass. The endpoint is documented as Alpha and Restricted. Cloudflare says cost and pricing fields may be absent until billing integration is complete. Missing or empty data is never interpreted as zero. Even when numeric costs are returned, this snapshot does not prove complete product coverage, every external writer, current R2/D1 headroom, invoices, or a project-specific zero-cost guarantee. The zero-cost conclusion remains UNKNOWN.

This workflow does not replace consumed subscription snapshot, R2 V0.3, usage audit, or bootstrap authorities. Never rerun any consumed one-time authority.

## Boundaries

No R2 object access, D1 query/provision/migration, provider request, market data, training, holdout access, source switch, model promotion, Cloud Paper runtime or schedule activation is permitted. An error or uncertain/ambiguous response must not trigger a retry or alternate source.

Cloud Paper remains disabled until account-wide usage, billing, all-writer coverage, fresh storage evidence, cost boundaries, and controlled acceptance are independently established under their applicable authorities.

## Official source

- [Cloudflare Get Account Usage V2 API](https://developers.cloudflare.com/api/resources/billing/subresources/usage/methods/get_account_usage_v2/) — endpoint, date-window semantics, daily billable metric records, Alpha/Restricted state, and notice that cost/pricing fields may be absent until billing integration is complete.


## Observed one-time execution result

- Workflow run: [36839577708](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36839577708), attempt 1, head `7c6bb943f74aebb08fa927e30730e23845825609`, event `workflow_dispatch`; completed with conclusion `failure`.
- The only Cloudflare request returned HTTP 403, exposed in the job log only as the fixed safe code `CLOUDFLARE_HTTP_403`. Available evidence does not identify whether this reflects endpoint access/entitlement, token permission, account scope, or another cause. Do not infer or publish a more specific diagnosis.
- No report file was produced and the artifact list is empty. The report-summary step recorded that no report file existed; artifact upload warned that the configured path had no files. The Actions run/job log is the preserved evidence.
- The one-time authority is `CONSUMED_DO_NOT_RERUN`, including after credential or settings changes. No retry was performed. Any further external query requires a distinct successor version and separate authority.
- `zero_cost=UNKNOWN`; complete billing and account-wide coverage remain unverified. Cloud Paper activation remains blocked. No R2/D1 access, runtime, or schedule activation occurred.
