# Cloud Paper billing metadata diagnostic V0.4 — synthetic preparation

## Why this exists

Billing History V0.3 run [37183381165](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37183381165) was consumed after one Cloudflare request and stopped at `BILLING_HISTORY_PAGE_METADATA_MISMATCH`. Its report did not identify which field mismatched. Do not rerun V0.3.

## Scope

This version contains only a pure parser, synthetic tests, and a prepared configuration. It has no workflow, Cloudflare client, credentials reference, network call, R2/D1 access, or external execution authority. CI can prove the parser reports page/per_page presence, JSON type, integer validity, and request-match booleans without copying response values.

The parser's `DIAGNOSTIC_COMPLETE` means only that the supplied synthetic response has matching request metadata. It does not establish Cloudflare billing readiness, full cost, zero cost, or Cloud Paper activation.

## Next gate

To identify the actual V0.3 mismatch, a separate successor execution authority must be versioned and merged, and the owner must separately approve the one-time Cloudflare GET. No dispatch is part of this preparation. If authorized later, the diagnostic must issue one page-1/per_page-100 GET only, with no retry or redirect, and emit only the value-free fields defined here. A failed or ambiguous attempt is consumed and cannot be rerun.

## Boundaries

No R2 or D1 access, no write or provisioning operation, no provider/training/holdout access, no schedule activation. Billing and zero-cost conclusions remain UNKNOWN; Cloud Paper stays disabled. The owner confirms no other current external R2 writers; future external writers must register before first write. This does not prove repository writer shared-admission coverage or D1 writer coverage.
