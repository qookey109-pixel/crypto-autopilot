# Cloud Paper account usage diagnostic V0.2

## Authority and purpose

This version is a separate, one-time successor to the consumed V0.1 Usage Audit. V0.1 run [36558934727](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36558934727) remains immutable evidence: it returned `REVIEW_REQUIRED / DATASET_EMPTY_UNVERIFIED` after one Cloudflare GraphQL request. V0.1 did not identify which dataset was empty. Do not rerun V0.1.

The V0.2 contract is `config/cloud_paper_usage_audit_v0_2.json`. The repeatable zero-network readiness workflow is `.github/workflows/cloud-paper-usage-audit-readiness-v0-2.yml`; the one-time live diagnostic is `.github/workflows/cloud-paper-usage-audit-v0-2.yml`. Both must run from protected `main`. V0.2 may be dispatched only after its own readiness reports `READY` on current main. A first V0.2 dispatch consumes its one-time authority even if it fails. Never rerun it.

## Credential boundary

Readiness passes only four booleans to the runner: Account ID Variable present, Account ID Secret present, read-only token Secret present, and Account ID Secret/Variable parity. It performs zero Cloudflare requests, does not expose either value, and does not prove API permission.

The live workflow passes the Account ID through the existing GitHub Actions **Secret** `CLOUDFLARE_ACCOUNT_ID`, not the Variable, and requires a nonempty match with the Variable before Cloudflare access. It uses only `CLOUDFLARE_READONLY_API_TOKEN` for GraphQL. If any name is absent or parity fails, it stops before the Cloudflare request. Do not paste token or Account ID values into chat, issues, PRs, logs, artifacts, or code.

## Bounded evidence

The live workflow checks its own run history and attempt number, then allows at most one Cloudflare GraphQL POST, with no retry, pagination, or redirect follow. Responses above 32 MiB fail closed. It asks for the same 30-day account-wide D1 rows/storage and R2 operations/storage datasets as V0.1. It does not query an individual database or bucket.

The V0.2 report records each dataset's state and group count separately. `EMPTY_UNVERIFIED`, `MISSING_OR_INVALID`, `INVALID_ROW`, and `LIMIT_REACHED` all produce `REVIEW_REQUIRED`; an empty dataset never means zero usage. If all four datasets are present, the existing aggregate parser checks fields and freshness, and the report remains review-only. Raw GraphQL responses, Account ID, database IDs, bucket names, and credentials are excluded from the report. The artifact expires after seven days; preserve run URL, attempt, head SHA, safe reason, and digest in project status after review.

An HTTP 403 or GraphQL error is a safe diagnostic of access/query failure; it does not justify broadening the token or changing provider. The report never activates Cloud Paper, D1, R2 writes, simulation, or a schedule.

## Cost and product boundary

[Cloudflare's GraphQL documentation](https://developers.cloudflare.com/analytics/graphql-api/) says aggregated analytics are not billing usage truth. D1 and R2 [analytics](https://developers.cloudflare.com/d1/observability/metrics-analytics/) [datasets](https://developers.cloudflare.com/r2/platform/metrics-analytics/) can help compare usage with free-tier ceilings, but they do not prove current invoice amount, plan, complete external-writer coverage, or future headroom. The consumed Billing Evidence run 36513941565 listed USD 0.00 subscription prices but did not include invoices or metered charges. `zero_cost_conclusion=UNKNOWN` and Cloud Paper activation remain closed until separate evidence and authority complete all gates.

This diagnostic does no R2 object access, D1 SQL/provisioning, provider access, holdout access, training, promotion, trading, or schedule activation. Mode stays `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`, `FREE-ONLY / 0 USD`, and PAPER/LIVE-PAPER only.
