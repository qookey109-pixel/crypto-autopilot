import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.bitget_macd_real_history import (
    BitgetMacdRealHistoryError,
    EXPECTED_DATASET_FINGERPRINT,
    expected_monthly_periods,
    select_governed_zec_15m_records,
    validate_contiguous_15m_history,
    validate_dataset_fingerprint,
)


def _record(period: str, *, symbol: str = "ZECUSDT", interval: str = "15m") -> dict:
    return {
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "r2_key": f"market-data/binance_usdm/crypto-core-v0.1/{symbol}/{interval}/{period}.parquet",
        "r2_sha256": "a" * 64,
        "source_rows": 100,
        "audit_ok": True,
    }


class BitgetMacdRealHistoryTests(unittest.TestCase):
    def test_expected_months_are_exactly_48(self) -> None:
        periods = expected_monthly_periods()
        self.assertEqual(len(periods), 48)
        self.assertEqual(periods[0], "2022-08")
        self.assertEqual(periods[-1], "2026-07")

    def test_selects_exact_governed_zec_15m_months(self) -> None:
        periods = expected_monthly_periods()
        catalog = {"markets": [{"symbol": "ZECUSDT", "asset_class": "crypto"}]}
        records = [_record(period) for period in periods]
        records.append(_record("2024-01", symbol="BTCUSDT"))

        selection = select_governed_zec_15m_records(
            catalog=catalog,
            object_records=records,
        )

        self.assertEqual(selection.partition_count, 48)
        self.assertEqual(selection.start_period, "2022-08")
        self.assertEqual(selection.end_period, "2026-07")
        self.assertEqual(len(selection.record_fingerprint), 64)

    def test_missing_month_fails_closed(self) -> None:
        periods = list(expected_monthly_periods())
        periods.remove("2024-06")
        catalog = {"markets": [{"symbol": "ZECUSDT", "asset_class": "crypto"}]}

        with self.assertRaisesRegex(BitgetMacdRealHistoryError, "2024-06"):
            select_governed_zec_15m_records(
                catalog=catalog,
                object_records=[_record(period) for period in periods],
            )

    def test_non_crypto_catalog_entry_fails(self) -> None:
        catalog = {"markets": [{"symbol": "ZECUSDT", "asset_class": "other"}]}
        with self.assertRaises(BitgetMacdRealHistoryError):
            select_governed_zec_15m_records(
                catalog=catalog,
                object_records=[_record(period) for period in expected_monthly_periods()],
            )

    def test_contiguous_15m_history_accepts_exact_sequence(self) -> None:
        step = 15 * 60 * 1000
        candles = [
            Candle(
                time_ms=index * step,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=10.0,
            )
            for index in range(8)
        ]
        validate_contiguous_15m_history(candles)

    def test_contiguous_15m_history_rejects_gap(self) -> None:
        step = 15 * 60 * 1000
        candles = [
            Candle(time_ms=0, open=1, high=1, low=1, close=1, volume=1),
            Candle(time_ms=step * 2, open=1, high=1, low=1, close=1, volume=1),
        ]
        with self.assertRaisesRegex(BitgetMacdRealHistoryError, "gap"):
            validate_contiguous_15m_history(candles)

    def test_dataset_fingerprint_is_frozen(self) -> None:
        validate_dataset_fingerprint(EXPECTED_DATASET_FINGERPRINT)
        with self.assertRaises(BitgetMacdRealHistoryError):
            validate_dataset_fingerprint("0" * 64)


if __name__ == "__main__":
    unittest.main()
