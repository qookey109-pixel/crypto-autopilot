# Cloud Paper account usage audit V0.1

## Purpose and authority

This is a one-time, manual, read-only calibration for Cloud Paper budget planning. Its contract is `config/cloud_paper_usage_audit_v0_1.json`; the execution workflow is `.github/workflows/cloud-paper-usage-audit-v0-1.yml`.

The separate readiness workflow checks only whether the named GitHub variable and secret are present. It performs zero network calls and does not consume the one-time execution. The secret value is never printed or copied to the report.

After the readiness run reports READY, the execution workflow may be dispatched once from protected `main`. It checks the GitHub workflow run history, requires run attempt 1, and stops on prior or ambiguous history before calling Cloudflare. The only Cloudflare call is one GraphQL analytics POST with a 30-day account-wide window and 10,000 groups maximum per dataset. HTTP retries, pagination, and reruns are forbidden. Any first execution attempt consumes the one-time authority, including a failed or incomplete capture.

The report is a secret-free GitHub Actions summary/artifact with seven-day artifact retention. It never stores the account ID, database IDs, bucket names, raw analytics response, or secret.

## Captured evidence

The request asks for account-wide D1 daily rows read/written and storage, plus R2 operation counts and storage. No database or bucket filter is sent. Empty, missing, partial, stale, or capped datasets are not treated as zero usage and return `REVIEW_REQUIRED`.

The report compares observed values with the configured D1/R2 Free-tier reference limits and the project's 8,000,000,000-byte R2 hard stop. These are comparison references only. Analytics do not establish the account's subscribed plan, billing amount, or every credential and external writer. The report therefore keeps `zero_cost_conclusion=UNKNOWN_PLAN_AND_BILLING_NOT_QUERIED` and `account_wide_writer_coverage=UNKNOWN_NOT_PROVEN`.

## Boundaries

The workflow performs no R2 object listing, object read/write/delete, S3 request, D1 SQL, migration, reservation settlement, provider call, training, holdout access, strategy promotion, trading, or schedule activation. It does not modify Cloud Paper activation, which remains disabled.

Cloudflare's official D1 docs describe account-wide rows and storage analytics with up to 31 days of metrics; its pricing page lists Workers Free allowances of 5M rows read/day, 100k rows written/day, and 5 GB storage. R2 analytics supports account-wide operation and storage datasets for up to 31 days; its Standard Free tier includes 10 GB-month storage, 1M Class A and 10M Class B requests. The current account plan and bill still require separate evidence.

Sources:
- [D1 metrics and analytics](https://developers.cloudflare.com/d1/observability/metrics-analytics/)
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [R2 metrics and analytics](https://developers.cloudflare.com/r2/platform/metrics-analytics/)
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
