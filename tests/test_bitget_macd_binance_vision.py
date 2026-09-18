import unittest
from dataclasses import replace

from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveReceipt,
    BinanceVisionKlineArchive,
)
from crypto_autopilot.models import Candle
from crypto_autopilot.research.bitget_macd_binance_vision import (
    combine_verified_zec_archives,
    zec_monthly_archive_keys,
)
from crypto_autopilot.research.bitget_macd_real_history import BitgetMacdRealHistoryError


class BitgetMacdBinanceVisionTests(unittest.TestCase):
    def test_archive_keys_are_frozen_to_48_zec_months(self) -> None:
        keys = zec_monthly_archive_keys()
        self.assertEqual(len(keys), 48)
        self.assertEqual(keys[0].symbol, "ZECUSDT")
        self.assertEqual(keys[0].interval, "15m")
        self.assertEqual(keys[0].period, "2022-08")
        self.assertEqual(keys[-1].period, "2026-07")
        self.assertTrue(keys[0].url.endswith("ZECUSDT-15m-2022-08.zip"))
        self.assertTrue(keys[0].checksum_url.endswith(".zip.CHECKSUM"))

    def test_archive_count_fails_closed(self) -> None:
        with self.assertRaisesRegex(BitgetMacdRealHistoryError, "expected 48"):
            combine_verified_zec_archives(())

    def test_identity_mismatch_fails_closed(self) -> None:
        key = zec_monthly_archive_keys()[0]
        receipt = BinanceVisionArchiveReceipt(
            dataset=key.dataset,
            frequency=key.frequency,
            symbol=key.symbol,
            interval=key.interval,
            period=key.period,
            source_url=key.url,
            checksum_url=key.checksum_url,
            archive_filename=key.filename,
            expected_sha256="a" * 64,
            archive_sha256="a" * 64,
            row_count=1,
            first_time_ms=0,
            last_time_ms=0,
            audit_ok=True,
        )
        archive = BinanceVisionKlineArchive(
            key=replace(key, period="2022-09"),
            candles=(Candle(time_ms=0, open=1, high=1, low=1, close=1, volume=1),),
            receipt=receipt,
        )
        with self.assertRaisesRegex(BitgetMacdRealHistoryError, "expected 48|identity mismatch"):
            combine_verified_zec_archives((archive,))


if __name__ == "__main__":
    unittest.main()
