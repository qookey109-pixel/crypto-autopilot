# Cloud Paper subscription billing snapshot V0.1

## Scope and authority

The versioned execution contract is `config/cloud_paper_billing_evidence_v0_1.json`. The manual workflow runs only from `main`, allows one run and one attempt, makes one GitHub Actions history request followed by at most one Cloudflare API request, and does not retry or paginate.

A separate readiness workflow checks that `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_BILLING_READONLY_API_TOKEN` are present. It performs zero network calls, prints no values, and does not consume the one-time audit. Run readiness first. The token must have only the required account-level Billing Read permission for this workflow; do not use Billing Edit or a global API key. Keep the token only in GitHub Actions Secrets.

The audit makes one GET to the account subscriptions endpoint with page 1 and a maximum page size of 20. A result is accepted only when page metadata proves the full subscription list fit in that one response. Incomplete, malformed, or ambiguous responses fail closed. The secret-free report omits the account ID, subscription IDs, plan display names, and raw API body.

## What the report establishes

The report records the observation time and each subscription's rate-plan identifier, state, listed USD price, and currency. It can show whether the listed subscription prices include a non-zero amount. It never describes the result as a zero-cost pass.

The endpoint does not report invoice totals or every metered charge. The conclusion remains `NOT_PROVEN_BY_SUBSCRIPTION_SNAPSHOT`. Review it alongside a fresh account-wide D1/R2 usage report and authoritative billing records. Do not infer missing values are zero.

The previous one-time usage audit V0.1 is unchanged and remains a separate authority. This subscription workflow neither consumes nor replaces it.

## Hard boundaries

This workflow does not inspect or modify invoices, payment methods, billing profiles, subscriptions, plan settings, or account members. It performs no D1 SQL/provisioning/migration, R2 object request, provider access, training, holdout access, trading, or schedule activation. Cloud Paper stays disabled.

## Official API references

- [Cloudflare List Subscriptions API](https://developers.cloudflare.com/api/resources/accounts/subresources/subscriptions/methods/get/) — account Billing Read is accepted; the response includes subscription plan and listed price fields.
- [Cloudflare Billing permissions](https://developers.cloudflare.com/billing/understand/billing-permissions/) — billing API tokens can use Billing Read or Billing Edit; this workflow requires read-only scope.

