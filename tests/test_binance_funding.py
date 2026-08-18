from __future__ import annotations

import hashlib
import io
import unittest
import zipfile

from crypto_autopilot.binance_funding import (
    BinanceFundingEvidenceError,
    BinanceFundingObservation,
    BinanceFundingRevisionConflictError,
    BinanceVisionFundingArchiveKey,
    assert_no_funding_archive_revision,
    combine_funding_archives,
    funding_r2_key,
    funding_to_parquet,
    ingest_funding_archive,
    parquet_to_funding,
)


def archive_payload(key: BinanceVisionFundingArchiveKey, csv_text: str) -> tuple[bytes, str]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(key.csv_filename, csv_text)
    payload = buffer.getvalue()
    sha = hashlib.sha256(payload).hexdigest()
    return payload, f"{sha}  {key.filename}\n"


class BinanceFundingTests(unittest.TestCase):
    def test_key_is_monthly_funding_rate_without_interval_subpath(self) -> None:
        key = BinanceVisionFundingArchiveKey("BTCUSDT", "2024-01")
        self.assertEqual(key.filename, "BTCUSDT-fundingRate-2024-01.zip")
        self.assertIn("/monthly/fundingRate/BTCUSDT/", key.url)
        self.assertNotIn("/1h/", key.url)
        self.assertEqual(
            funding_r2_key("BTCUSDT", 2024),
            "market-data/binance_usdm/perp/BTCUSDT/funding/year=2024/funding.parquet",
        )

    def test_ingest_headerless_three_column_archive_and_parquet_round_trip(self) -> None:
        key = BinanceVisionFundingArchiveKey("BTCUSDT", "2024-01")
        csv_text = "\n".join(
            [
                "1704067200000,8,0.00010000",
                "1704096000000,8,-0.00005000",
                "1704124800000,8,0.00002000",
            ]
        ) + "\n"
        payload, checksum = archive_payload(key, csv_text)
        result = ingest_funding_archive(key, archive_bytes=payload, checksum_payload=checksum)
        self.assertTrue(result.receipt.audit_ok)
        self.assertEqual(result.receipt.row_count, 3)
        self.assertEqual(result.receipt.interval_hours, (8,))
        self.assertEqual(result.receipt.cadence_anomalies, 0)
        self.assertFalse(result.receipt.native_to_pionex)

        artifact = funding_to_parquet(result.observations)
        decoded = parquet_to_funding(artifact.payload)
        self.assertEqual(decoded, list(result.observations))
        self.assertEqual(artifact.rows, 3)

    def test_header_schema_is_supported_and_interval_transition_is_not_synthetic_gap(self) -> None:
        key = BinanceVisionFundingArchiveKey("ETHUSDT", "2024-01")
        csv_text = "\n".join(
            [
                "calc_time,funding_interval_hours,last_funding_rate",
                "1704067200000,8,0.0001",
                "1704096000000,4,0.0002",
                "1704110400000,4,0.0003",
            ]
        ) + "\n"
        payload, checksum = archive_payload(key, csv_text)
        result = ingest_funding_archive(key, archive_bytes=payload, checksum_payload=checksum)
        self.assertEqual(result.receipt.interval_hours, (4, 8))

    def test_unexplained_gap_fails_closed(self) -> None:
        key = BinanceVisionFundingArchiveKey("SOLUSDT", "2024-01")
        csv_text = "\n".join(
            [
                "1704067200000,8,0.0001",
                "1704106800000,8,0.0002",
            ]
        ) + "\n"
        payload, checksum = archive_payload(key, csv_text)
        with self.assertRaises(BinanceFundingEvidenceError):
            ingest_funding_archive(key, archive_bytes=payload, checksum_payload=checksum)

    def test_checksum_and_revision_conflicts_fail_closed(self) -> None:
        key = BinanceVisionFundingArchiveKey("BTCUSDT", "2024-01")
        csv_text = "1704067200000,8,0.0001\n1704096000000,8,0.0002\n"
        payload, checksum = archive_payload(key, csv_text)
        result = ingest_funding_archive(key, archive_bytes=payload, checksum_payload=checksum)
        bad_checksum = "0" * 64 + f"  {key.filename}\n"
        with self.assertRaises(BinanceFundingEvidenceError):
            ingest_funding_archive(key, archive_bytes=payload, checksum_payload=bad_checksum)

        changed = result.receipt.__class__(
            **{
                **{name: getattr(result.receipt, name) for name in result.receipt.__dataclass_fields__},
                "archive_sha256": "f" * 64,
            }
        )
        with self.assertRaises(BinanceFundingRevisionConflictError):
            assert_no_funding_archive_revision(result.receipt, changed)

    def test_annual_combine_rejects_cross_symbol_or_duplicate_times(self) -> None:
        key = BinanceVisionFundingArchiveKey("BTCUSDT", "2024-01")
        payload, checksum = archive_payload(
            key,
            "1704067200000,8,0.0001\n1704096000000,8,0.0002\n",
        )
        archive = ingest_funding_archive(key, archive_bytes=payload, checksum_payload=checksum)
        combined = combine_funding_archives([archive], symbol="BTCUSDT", year=2024)
        self.assertEqual(len(combined), 2)
        with self.assertRaises(BinanceFundingEvidenceError):
            combine_funding_archives([archive], symbol="ETHUSDT", year=2024)

    def test_observation_rejects_nonfinite_rate(self) -> None:
        with self.assertRaises(ValueError):
            BinanceFundingObservation("BTCUSDT", 1, 8, float("nan"))


if __name__ == "__main__":
    unittest.main()
