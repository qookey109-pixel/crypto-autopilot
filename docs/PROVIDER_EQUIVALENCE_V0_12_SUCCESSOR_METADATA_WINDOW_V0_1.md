# Provider Equivalence V0.12 Successor Metadata Window V0.1

## Outcome

V0.12 is an atomic successor to the incomplete V0.10 scheduled metadata
window. On the exact protected-main merge it removes the V0.10 cron and enables
one independent 194-slot metadata-only window:

- start: `2026-09-04T02:00:00Z`;
- end: `2026-09-12T03:59:59.999Z`;
- scheduled attempts: `:17` and `:47` UTC in every one of the 194 hours;
- providers: Pionex and Binance USD-M remain separate;
- storage: a new immutable V0.12 R2 namespace;
- budget: `0 USD/month`, with the existing 8 GB whole-bucket hard stop.

V0.10 missing and failed slots remain failures. They are not replayed,
backfilled, regraded or copied into V0.12.

`workflow_dispatch` validates the authority and parser only. The capture CLI
also requires `GITHUB_EVENT_NAME=schedule`, so manual events stop before any
provider request or R2 client construction.

## Pionex response adapter

The official Pionex futures documentation currently describes the newer
`contractType` / `status` representation, while the public common-symbols
response observed by V0.10 did not preserve both required fields. The same
official endpoint also documents the legacy `type` / `enable` representation.

V0.12 freezes an explicit adapter instead of weakening validation:

| Meaning | Preferred field | Allowed fallback | Normalized value |
| --- | --- | --- | --- |
| perpetual contract | `contractType=PERPETUAL` | `type=PERP` | `PERPETUAL` |
| trading | `status=TRADING` | `enable=true` | `TRADING` |
| offline | `status=OFFLINE` | `enable=false` | `OFFLINE` |
| price increment | `quoteStep` | none | exact positive source string |

If preferred and fallback fields are both present they must agree. Missing,
unknown or contradictory values fail before R2 client construction. Raw Pionex
bytes are preserved under Pionex provenance and are never relabeled.

Official contract reference:
<https://www.pionex.com/docs/api-docs/futures-api/common>.

## Stability contract frozen before evidence

A future evaluation requires at least one complete valid V0.12 receipt in each
of the 194 UTC hourly slots. Duplicates are valid only when provider vectors
agree exactly inside the slot, and each provider vector must remain exactly
stable across the full window. Missing, invalid or conflicting evidence fails.

This authority does not authorize the future R2 receipt read/evaluation. That
still requires a separate versioned production-evaluation authority after the
window ends.

## Prohibited

- V0.10 replay or backfill;
- holdout candle listing, reading or evaluation;
- source switching, provider splicing or Pionex relabeling;
- historical-universe admission or W1 materialization;
- strategy/risk changes or automatic model promotion;
- trade plans, real-money orders or live trading;
- paid cloud fallback or Render receipt of R2 credentials.
