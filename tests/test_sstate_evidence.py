from __future__ import annotations

import unittest

from crypto_autopilot.sstate_evidence import (
    AvailabilityBasis,
    EvidenceKind,
    EvidenceStatus,
    SStateEvidenceError,
    SStateEvidenceManifest,
    SStateEvidenceRecord,
    encode_sstate_evidence_records,
    ingest_sstate_evidence_bundle,
    payload_sha256,
)


FOUR_HOURS_MS = 4 * 60 * 60 * 1000


def _record(
    *,
    symbol: str = "BTC_USDT_PERP",
    bar_time_ms: int = 0,
    available_at_ms: int = FOUR_HOURS_MS,
) -> SStateEvidenceRecord:
    return SStateEvidenceRecord(
        symbol=symbol,
        bar_time_ms=bar_time_ms,
        available_at_ms=available_at_ms,
        state="S3",
        probability=0.67,
        samples=123,
        available=True,
    )


def _manifest(
    payload: bytes,
    *,
    kind: EvidenceKind = EvidenceKind.REAL_RECORDED,
    basis: AvailabilityBasis = AvailabilityBasis.RECORDED_RUNTIME,
    status: EvidenceStatus = EvidenceStatus.PASS,
    generated_at_ms: int = FOUR_HOURS_MS + 1000,
    record_count: int = 1,
) -> SStateEvidenceManifest:
    return SStateEvidenceManifest(
        evidence_id="sstate-real-proof-001",
        status=status,
        evidence_kind=kind,
        availability_basis=basis,
        interval="4H",
        producer_ref="sstate-core:pinned-v0.1-fixture-ref",
        producer_sha256="a" * 64,
        source_ref="r2://authority/sstate-real-proof-001.json",
        payload_sha256=payload_sha256(payload),
        record_count=record_count,
        generated_at_ms=generated_at_ms,
    )


class HistoricalSStateEvidenceTest(unittest.TestCase):
    def test_canonical_encoding_is_deterministic_and_sorted(self) -> None:
        later = _record(symbol="ETH_USDT_PERP", bar_time_ms=FOUR_HOURS_MS, available_at_ms=2 * FOUR_HOURS_MS)
        earlier = _record(symbol="BTC_USDT_PERP")

        forward = encode_sstate_evidence_records((later, earlier))
        reverse = encode_sstate_evidence_records((earlier, later))

        self.assertEqual(forward, reverse)
        self.assertEqual(payload_sha256(forward), payload_sha256(reverse))

    def test_duplicate_symbol_bar_identity_is_rejected(self) -> None:
        record = _record()
        with self.assertRaisesRegex(SStateEvidenceError, "duplicate symbol/bar identity"):
            encode_sstate_evidence_records((record, record))

    def test_fixture_evidence_cannot_become_historical_authority(self) -> None:
        payload = encode_sstate_evidence_records((_record(),))
        manifest = _manifest(payload, kind=EvidenceKind.FIXTURE)

        with self.assertRaisesRegex(SStateEvidenceError, "fixture SState evidence"):
            ingest_sstate_evidence_bundle(
                payload=payload,
                manifest=manifest,
                ingestion_time_ms=manifest.generated_at_ms,
            )

    def test_reconstructed_availability_is_rejected_in_v0_1(self) -> None:
        payload = encode_sstate_evidence_records((_record(),))
        manifest = _manifest(payload, basis=AvailabilityBasis.RECONSTRUCTED)

        with self.assertRaisesRegex(SStateEvidenceError, "reconstructed SState availability"):
            ingest_sstate_evidence_bundle(
                payload=payload,
                manifest=manifest,
                ingestion_time_ms=manifest.generated_at_ms,
            )

    def test_payload_sha_mismatch_is_rejected(self) -> None:
        payload = encode_sstate_evidence_records((_record(),))
        manifest = SStateEvidenceManifest(
            evidence_id="bad-sha",
            status=EvidenceStatus.PASS,
            evidence_kind=EvidenceKind.REAL_RECORDED,
            availability_basis=AvailabilityBasis.RECORDED_RUNTIME,
            interval="4H",
            producer_ref="producer",
            producer_sha256="b" * 64,
            source_ref="source",
            payload_sha256="c" * 64,
            record_count=1,
            generated_at_ms=FOUR_HOURS_MS + 1000,
        )

        with self.assertRaisesRegex(SStateEvidenceError, "payload SHA-256 mismatch"):
            ingest_sstate_evidence_bundle(
                payload=payload,
                manifest=manifest,
                ingestion_time_ms=manifest.generated_at_ms,
            )

    def test_output_cannot_be_available_before_its_four_hour_bar_closes(self) -> None:
        record = _record(available_at_ms=FOUR_HOURS_MS - 1)
        payload = encode_sstate_evidence_records((record,))
        manifest = _manifest(payload)

        with self.assertRaisesRegex(SStateEvidenceError, "before its 4H bar closes"):
            ingest_sstate_evidence_bundle(
                payload=payload,
                manifest=manifest,
                ingestion_time_ms=manifest.generated_at_ms,
            )

    def test_manifest_generation_time_cannot_be_in_ingestion_future(self) -> None:
        payload = encode_sstate_evidence_records((_record(),))
        manifest = _manifest(payload, generated_at_ms=FOUR_HOURS_MS + 5000)

        with self.assertRaisesRegex(SStateEvidenceError, "ingestion future"):
            ingest_sstate_evidence_bundle(
                payload=payload,
                manifest=manifest,
                ingestion_time_ms=FOUR_HOURS_MS + 4999,
            )

    def test_noncanonical_payload_is_rejected_even_with_matching_sha(self) -> None:
        canonical = encode_sstate_evidence_records((_record(),))
        noncanonical = canonical + b"\n"
        manifest = _manifest(noncanonical)

        with self.assertRaisesRegex(SStateEvidenceError, "canonical encoding"):
            ingest_sstate_evidence_bundle(
                payload=noncanonical,
                manifest=manifest,
                ingestion_time_ms=manifest.generated_at_ms,
            )

    def test_valid_real_recorded_bundle_maps_exact_context_into_replay_points(self) -> None:
        record = _record()
        payload = encode_sstate_evidence_records((record,))
        manifest = _manifest(payload)

        verified = ingest_sstate_evidence_bundle(
            payload=payload,
            manifest=manifest,
            ingestion_time_ms=manifest.generated_at_ms,
        )

        self.assertEqual(verified.point_count, 1)
        self.assertEqual(verified.payload_sha256, payload_sha256(payload))
        self.assertEqual(verified.first_bar_time_ms, 0)
        self.assertEqual(verified.last_bar_time_ms, 0)
        point = verified.points[0]
        self.assertEqual(point.symbol, record.symbol)
        self.assertEqual(point.bar_time_ms, record.bar_time_ms)
        self.assertEqual(point.available_at_ms, record.available_at_ms)
        self.assertEqual(point.context.state, record.state)
        self.assertEqual(point.context.probability, record.probability)
        self.assertEqual(point.context.samples, record.samples)
        self.assertEqual(point.context.available, record.available)
        self.assertEqual(point.source_sha256, payload_sha256(payload))
        self.assertIn(manifest.evidence_id, point.source_ref)


if __name__ == "__main__":
    unittest.main()
