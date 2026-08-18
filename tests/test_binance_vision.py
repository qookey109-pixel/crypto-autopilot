from __future__ import annotations

import hashlib
import io
import unittest
import zipfile
from dataclasses import replace

from crypto_autopilot.binance_historical import BINANCE_INTERVAL_MS
from crypto_autopilot.binance_vision import (
    BinanceVisionArchiveKey,
    BinanceVisionEvidenceError,
    BinanceVisionRevisionConflictError,
    assert_no_archive_revision,
    ingest_kline_archive,
    ingest_mark_price_archive,
    parse_checksum,
)


def make_zip(filename: str, rows: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, "\n".join(rows) + "\n")
    return buffer.getvalue()


def checksum_for(filename: str, payload: bytes) -> str:
    return f"{hashlib.sha256(payload).hexdigest()}  {filename}\n"


class BinanceVisionTests(unittest.TestCase):
    def test_monthly_urls_follow_official_um_path_contract(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "BTCUSDT", "15m", "2025-01")
        self.assertEqual(key.filename, "BTCUSDT-15m-2025-01.zip")
        self.assertEqual(
            key.path,
            "data/futures/um/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-2025-01.zip",
        )
        self.assertEqual(key.checksum_url, key.url + ".CHECKSUM")

        daily = BinanceVisionArchiveKey("markPriceKlines", "daily", "ETHUSDT", "1h", "2025-01-02")
        self.assertIn("/daily/markPriceKlines/ETHUSDT/1h/", daily.url)

    def test_checksum_parser_accepts_standard_sha256_format(self) -> None:
        digest = "a" * 64
        self.assertEqual(parse_checksum(f"{digest}  BTCUSDT-15m-2025-01.zip\n"), (digest, "BTCUSDT-15m-2025-01.zip"))
        self.assertEqual(parse_checksum(f"{digest} *BTCUSDT-15m-2025-01.zip"), (digest, "BTCUSDT-15m-2025-01.zip"))
        with self.assertRaises(BinanceVisionEvidenceError):
            parse_checksum("not-a-checksum")

    def test_kline_archive_requires_checksum_and_strict_candle_audit(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "BTCUSDT", "15m", "2025-01")
        step = BINANCE_INTERVAL_MS["15m"]
        rows = [
            "open_time,open,high,low,close,volume,close_time,quote_volume,trades,taker_base,taker_quote,ignore",
            f"0,100,102,99,101,10,{step - 1},0,1,0,0,0",
            f"{step},101,103,100,102,11,{2 * step - 1},0,1,0,0,0",
            f"{2 * step},102,104,101,103,12,{3 * step - 1},0,1,0,0,0",
        ]
        payload = make_zip(key.csv_filename, rows)
        result = ingest_kline_archive(
            key,
            archive_bytes=payload,
            checksum_payload=checksum_for(key.filename, payload),
        )
        self.assertEqual(len(result.candles), 3)
        self.assertTrue(result.receipt.audit_ok)
        self.assertEqual(result.receipt.provider, "binance_usdm")
        self.assertFalse(result.receipt.native_to_pionex)
        self.assertFalse(result.receipt.may_authorize_pionex_native_history)

        bad_checksum = f"{'0' * 64}  {key.filename}\n"
        with self.assertRaises(BinanceVisionEvidenceError):
            ingest_kline_archive(key, archive_bytes=payload, checksum_payload=bad_checksum)

    def test_kline_archive_rejects_gap_instead_of_interpolating(self) -> None:
        key = BinanceVisionArchiveKey("klines", "daily", "BTCUSDT", "1h", "2025-01-02")
        step = BINANCE_INTERVAL_MS["1h"]
        rows = [
            f"0,100,102,99,101,10,{step - 1},0,1,0,0,0",
            f"{2 * step},102,104,101,103,12,{3 * step - 1},0,1,0,0,0",
        ]
        payload = make_zip(key.csv_filename, rows)
        with self.assertRaises(BinanceVisionEvidenceError):
            ingest_kline_archive(
                key,
                archive_bytes=payload,
                checksum_payload=checksum_for(key.filename, payload),
            )

    def test_mark_price_archive_is_closed_bar_and_contiguous(self) -> None:
        key = BinanceVisionArchiveKey("markPriceKlines", "monthly", "BTCUSDT", "4h", "2025-01")
        step = BINANCE_INTERVAL_MS["4h"]
        rows = [
            f"0,100,102,99,101,0,{step - 1},0,0,0,0,0",
            f"{step},101,103,100,102,0,{2 * step - 1},0,0,0,0,0",
        ]
        payload = make_zip(key.csv_filename, rows)
        result = ingest_mark_price_archive(
            key,
            archive_bytes=payload,
            checksum_payload=checksum_for(key.filename, payload),
        )
        self.assertEqual(result.candles[0].available_at_ms, step)
        self.assertEqual(result.candles[1].available_at_ms, 2 * step)
        self.assertEqual(result.receipt.row_count, 2)

    def test_archive_member_name_must_match_logical_archive(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "BTCUSDT", "15m", "2025-01")
        payload = make_zip("wrong.csv", ["0,1,2,0.5,1.5,1,899999,0,1,0,0,0"])
        with self.assertRaises(BinanceVisionEvidenceError):
            ingest_kline_archive(
                key,
                archive_bytes=payload,
                checksum_payload=checksum_for(key.filename, payload),
            )

    def test_archive_revision_requires_explicit_review(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "BTCUSDT", "15m", "2025-01")
        step = BINANCE_INTERVAL_MS["15m"]
        rows = [f"0,100,102,99,101,10,{step - 1},0,1,0,0,0"]
        payload = make_zip(key.csv_filename, rows)
        result = ingest_kline_archive(
            key,
            archive_bytes=payload,
            checksum_payload=checksum_for(key.filename, payload),
        )
        assert_no_archive_revision(result.receipt, result.receipt)

        revised = replace(result.receipt, archive_sha256="f" * 64, expected_sha256="f" * 64)
        with self.assertRaises(BinanceVisionRevisionConflictError):
            assert_no_archive_revision(result.receipt, revised)

    def test_key_validation_rejects_invalid_periods_and_provider_shapes(self) -> None:
        with self.assertRaises(ValueError):
            BinanceVisionArchiveKey("klines", "monthly", "btcusdt", "15m", "2025-01")
        with self.assertRaises(ValueError):
            BinanceVisionArchiveKey("klines", "monthly", "BTCUSDT", "15m", "2025-13")
        with self.assertRaises(ValueError):
            BinanceVisionArchiveKey("fundingRate", "monthly", "BTCUSDT", "15m", "2025-01")


if __name__ == "__main__":
    unittest.main()
