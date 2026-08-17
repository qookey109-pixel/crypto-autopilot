import unittest
from datetime import datetime, timezone

from crypto_autopilot.storage.layout import HistoricalObjectKey, manifest_key, receipt_key


class StorageLayoutTests(unittest.TestCase):
    def test_monthly_15m_partition_key_is_stable(self) -> None:
        key = HistoricalObjectKey(
            exchange="pionex",
            market_type="perp",
            symbol="BTC_USDT_PERP",
            interval="15M",
            year=2026,
            month=8,
        ).build()
        self.assertEqual(
            key,
            "market-data/pionex/perp/BTC_USDT_PERP/15m/year=2026/month=08/candles.parquet",
        )

    def test_annual_4h_partition_key_is_stable(self) -> None:
        key = HistoricalObjectKey(
            exchange="pionex",
            market_type="perp",
            symbol="ETH_USDT_PERP",
            interval="4H",
            year=2025,
        ).build()
        self.assertEqual(
            key,
            "market-data/pionex/perp/ETH_USDT_PERP/4h/year=2025/candles.parquet",
        )

    def test_receipt_and_manifest_keys(self) -> None:
        self.assertEqual(receipt_key("run/123"), "receipts/historical/run-123.json")
        dt = datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc)
        self.assertEqual(
            manifest_key(dt),
            "manifests/historical/year=2026/month=08/manifest-20260817T080000Z.json",
        )


if __name__ == "__main__":
    unittest.main()
