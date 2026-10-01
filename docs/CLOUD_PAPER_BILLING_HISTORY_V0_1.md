# Cloud Paper account billing history V0.1

## Purpose and authority

This is a new, one-time, read-only evidence scope. Its versioned contract is [config/cloud_paper_billing_history_v0_1.json](../config/cloud_paper_billing_history_v0_1.json). It supplements the already-consumed subscription and billable-usage snapshots; it does not rerun either one.

The workflow is manual-dispatch on protected `main`, one run and one attempt. It first checks GitHub workflow history, then reads at most ten sequential pages of the Cloudflare account billing-history endpoint (100 items per page; at most 1,000 items total). It does not retry, follow redirects, apply a status filter, or continue beyond the caps. If total_count exceeds the cap, page metadata is inconsistent, or a request fails, the report preserves a safe reason code and marks coverage incomplete. No rerun is allowed.

## Data minimization

The [Get Account Billing History API](https://developers.cloudflare.com/api/resources/billing/subresources/history/methods/list/) accepts Account Billing Read and returns billing item amounts, amount-to-pay, currency, categories, occurrence time, invoice identifiers, and hosted invoice URLs. The collector only persists the occurrence month, safe categorical fields, amount fields, and pagination counts. It discards account/item/invoice identifiers, URLs, descriptions, and raw responses. Amounts remain item-level: the report deliberately does not sum billing history because charges, invoices, credits, and payments can overlap and double-count.

## What the result means

A complete bounded result can establish what the endpoint returned for the account history at the observation time. It is not a current-period usage meter, does not establish future cost, does not prove all products or writers are covered, and does not prove zero total cost. The report always leaves the zero-cost conclusion `UNKNOWN` and Cloud Paper disabled. Reconcile with subscription, usage, official invoices, current plan, resource usage/headroom, and a maintained inventory of every writer before production use.

The owner expects additional Cloudflare projects/services may be added later. Every new writer must be registered and adopt the shared admission contract before its first write; unregistered writers remain outside repository-enforced controls, so an incomplete account inventory continues to block production Cloud Paper writes.

## Validation and hard boundaries

Synthetic CI covers complete pagination, cap truncation, duplicate IDs across pages, malformed metadata, unsafe identity-field redaction, and amount validation. These tests do not call Cloudflare. No D1/R2/provider/exchange access, provisioning, runtime activation, training, holdout access, or schedule activation is included.

The one-shot dispatch is separate from CI and is not part of this code change. Once this authority is merged, the configured workflow can be manually dispatched on `main`; it must not be rerun even if the result is incomplete or fails.
