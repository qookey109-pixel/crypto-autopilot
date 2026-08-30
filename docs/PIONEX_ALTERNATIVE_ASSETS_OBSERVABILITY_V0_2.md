# Pionex Alternative Assets Observability V0.2

## Outcome

V0.2 replaces the unexecuted V0.1 schedule with one bounded metadata-only
workflow. The V0.1 file remains the 125-candidate registry; V0.2 validates the
actual Pionex `PERP + TRADING` intersection, compares it with the prior verified
V0.2 catalog, estimates storage capacity and emits a safe aggregate projection.

It begins no earlier than `2026-09-04T02:00:00Z`, first runs at
`2026-09-04T02:53:00Z`, repeats on September 6, 13, 20 and 27 at `03:53 UTC`,
and expires before provider or R2 access at `2026-10-01T00:00:00Z`.

## Validation and weekly difference

Each catalog must preserve provider/schema identity, metadata-only authority,
unique selected symbols and bases, exact asset-class counts, and a complete
matched/absent partition of the 125 candidates. Unknown `X`-suffix markets are
review-only and never selected automatically.

The first valid run creates a baseline. Later runs report added symbols,
currently absent symbols and any class mismatch. A count below 50% of the prior
valid catalog or an asset-class change becomes `REVIEW_REQUIRED`. Absence from
one catalog is not delisting proof and never mutates the registry.

## Capacity projection

The four-year planning model uses 1,461 days and `96 + 24 + 6` rows per market
per day for `15M / 60M / 4H`. For all 125 candidates this is 23,010,750 rows:

| Assumption | Canonical | With 1.25x operational stress |
| --- | ---: | ---: |
| 32 bytes/row | 0.74 GB | 0.92 GB |
| 64 bytes/row | 1.47 GB | 1.84 GB |
| 128 bytes/row | 2.95 GB | 3.68 GB |

These are decimal-GB planning figures, not provider availability evidence and
not authority to download or retain history. Real Parquet compression must be
measured under a separately approved pilot.

## Storage and website

Before any prior-catalog/provider access and again before writes, the workflow
applies the fresh whole-bucket 8 GB FREE-ONLY headroom gate. Catalog, analysis,
safe projection and manifest objects are immutable and SHA-256 read back; the
latest pointer is written last.

The website displays only aggregate candidate counts, observed match counts,
diff counts and capacity. It never exposes the raw symbol catalog. The schedule
does not deploy Pages; its safe projection remains R2/Actions evidence until a
reviewed Repository refresh.

## Authority boundary

No K-line, funding, trade or order-book endpoint is authorized. V0.2 does not
open the replacement holdout, materialize history, train or promote models,
create trade plans, call a private API, submit demo/real orders or enable live
trading. Equity-token, ETF/fund and metal histories remain separate future data
and model authorities rather than being mixed into Crypto Core 100.
