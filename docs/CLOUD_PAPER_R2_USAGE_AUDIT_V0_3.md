# Cloud Paper R2 usage diagnostic V0.3

## Authority and purpose

The V0.3 contract is `config/cloud_paper_r2_usage_audit_v0_3.json`. It is a separately versioned, one-time successor. V0.1 run 36558934727 and V0.2 run 36584465739 remain immutable and consumed; never rerun either. The V0.2 R2 operations query grouped by both action type and datetime and returned the 10000-group cap. V0.3 removes datetime from the operations dimensions and requests only action type groups. Cloudflare's official R2 example uses the same account-level operations aggregation pattern.

V0.3 becomes executable only after the contract is merged to protected main. Run the zero-network readiness workflow on current main first. A first live dispatch consumes the authority even if GitHub history or Cloudflare access fails; no retry, rerun, or pagination.

## Scope and limits

One GitHub Actions history request is allowed to prove that the current dispatch is the only V0.3 run; one Cloudflare GraphQL POST is allowed. Both have 20-second request timeouts. Cloudflare redirects are rejected, response bodies are capped at 32 MiB, and the workflow times out after five minutes.

The 30-day query requests only account-level R2 operations and storage. Operation groups are limited to 100 with dimensions `actionType` only. Storage groups are limited to 10000, retain `bucketName` and `datetime` only in runner memory, and the report contains only aggregate counts/bytes and snapshot times. No account ID, bucket name, credential, or raw response is written to the report or artifact.

The storage summary chooses the latest returned snapshot per returned bucket. Its scope is **the buckets represented in the analytics response**. Analytics alone does not prove inventory completeness or shared-account writer coverage. Operation grouping removes the timestamp dimension; operation-data freshness remains unknown. A report with both datasets present and storage samples within 48 hours is `READY_FOR_REVIEW`, not a budget pass.

## What the report cannot establish

V0.3 does not query D1 inventory or usage, subscription pricing, invoices, billable charges, all account writers, or project-specific spend. The configured 8,000,000,000-byte safety ceiling is displayed only as policy context; this report cannot open the storage headroom gate. Zero cost remains `UNKNOWN`. Cloud Paper activation, D1 provisioning, writes, and natural execution remain disabled.

Cloudflare's D1 List Databases endpoint accepts D1 Read or D1 Write, which is a separate permission from Account Analytics. The existing analytics token must not be broadened silently; a future D1 inventory stage needs its own least-privilege read token and versioned authority. The V1 billable-usage API is currently documented as deprecated; the billing history API accepts Billing Read but does not by itself prove unbilled current-period usage.

## Validation

Synthetic CI covers grouped operations, latest-per-bucket aggregation, limits, empty/stale/conflicting datasets, malformed metrics, readiness semantics, and report redaction. Cloud CI is implementation evidence only. The V0.3 readiness run, live audit result, account billing, product integration, and natural schedule evidence are separate stages.

## Official references

- [R2 metrics and analytics](https://developers.cloudflare.com/r2/platform/metrics-analytics/)
- [Cloudflare GraphQL Analytics API](https://developers.cloudflare.com/analytics/graphql-api/)
- [D1 List Databases API](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/list/)
- [Billing usage API](https://developers.cloudflare.com/api/resources/billing/subresources/usage/)
- [Account billing history API](https://developers.cloudflare.com/api/resources/billing/subresources/history/methods/list/)
- [Monitor billable usage](https://developers.cloudflare.com/billing/manage/billable-usage/)
