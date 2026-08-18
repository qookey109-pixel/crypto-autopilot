# Historical SState Evidence Ingestion V0.1

## Purpose

Define the authority boundary between a real historical SState evidence artifact and the existing read-only `HistoricalSStateReplayProvider`.

This layer does not calculate SState and does not modify SState core. It verifies evidence provenance, timing and integrity before converting records into `HistoricalSStatePoint` objects.

## Why this exists

The replay provider already prevents exact-bar carry-forward and future reads, but a replay point is only as trustworthy as the evidence used to construct it.

Historical backtests must not silently treat any of the following as real historical SState authority:

- unit-test fixtures;
- manually fabricated JSON;
- after-the-fact reconstructed SState outputs that claim a historical availability time without a separate reconstruction proof;
- payloads whose SHA-256 does not match the receipt;
- SState outputs timestamped before the 4H input bar was actually closed.

## Frozen record schema

Canonical payload schema:

`historical-sstate-records-v0.1`

Each row contains exactly:

- `symbol`
- `bar_time_ms`
- `available_at_ms`
- `state`
- `probability`
- `samples`
- `available`

Rows are canonicalized by `(bar_time_ms, symbol)`. Duplicate `symbol + bar_time_ms` identities are rejected.

The JSON encoding is deterministic. Reordering input records produces identical bytes and therefore the same SHA-256.

## Manifest contract

`SStateEvidenceManifest` freezes:

- `evidence_id`
- `status`
- `evidence_kind`
- `availability_basis`
- `interval`
- `producer_ref`
- `producer_sha256`
- `source_ref`
- `payload_sha256`
- `record_count`
- `generated_at_ms`

Both producer and payload hashes use 64-character SHA-256 hex digests.

## V0.1 admission policy

Historical replay admission currently requires all of the following:

1. manifest status is `PASS`;
2. evidence kind is `REAL_RECORDED`;
3. availability basis is `RECORDED_RUNTIME`;
4. interval is exactly `4H` for SState Intraday Wave V0.1;
5. manifest generation time is not in the ingestion future;
6. payload SHA-256 matches the manifest;
7. payload uses the exact canonical encoding;
8. manifest record count matches the decoded record count;
9. every bar is aligned to the 4H grid;
10. every `available_at_ms` is at or after that 4H bar's close;
11. no record claims availability later than the manifest generation time.

Only after those checks pass are records converted into `HistoricalSStatePoint` objects.

## Fixture rejection

`EvidenceKind.FIXTURE` is always rejected from historical authority.

Fixtures remain valid for unit tests of schemas and replay mechanics, but a test passing does not transform a fixture into market evidence.

## Reconstruction boundary

`AvailabilityBasis.RECONSTRUCTED` is intentionally rejected in V0.1.

An after-the-fact deterministic reconstruction may eventually be useful, but it requires a separate proof covering at least:

- pinned SState producer/core version;
- exact historical inputs available at each bar;
- deterministic reproduction;
- no future-data dependency;
- an explicit reconstructed-availability policy.

Until that proof exists, reconstruction is not equivalent to contemporaneously recorded runtime evidence.

## Relationship to replay

```text
real recorded SState export
        ↓
canonical payload + manifest
        ↓
Historical SState Evidence Ingestion V0.1
  - schema
  - SHA-256
  - provenance
  - timing
  - real-vs-fixture gate
        ↓
HistoricalSStatePoint
        ↓
HistoricalSStateReplayProvider
        ↓
Strategy Replay Readiness
```

The evidence payload SHA-256 is copied into every generated replay point, while the point source reference includes the evidence id.

## What this does not prove

This implementation is an ingestion contract only. The Repository does not yet contain a real historical SState evidence bundle that has passed this gate.

Therefore:

- real historical SState evidence remains incomplete;
- automatic historical trade-plan generation remains unauthorized;
- `trade_plan_authorized` remains false;
- no profitability claim is created.

## Safety

- SState core remains read-only and unmodified.
- No private Pionex API is introduced.
- No live orders are introduced.
- No reconstructed evidence is mislabeled as recorded runtime evidence.
- No live-trading authorization is created.
