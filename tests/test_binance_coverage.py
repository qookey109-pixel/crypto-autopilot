from __future__ import annotations

import unittest

from crypto_autopilot.binance_coverage import month_periods, summarize_presence


class BinanceCoverageTests(unittest.TestCase):
    def test_month_periods_cross_year(self) -> None:
        self.assertEqual(
            month_periods("2025-11", "2026-02"),
            ("2025-11", "2025-12", "2026-01", "2026-02"),
        )

    def test_month_periods_rejects_reverse_range(self) -> None:
        with self.assertRaises(ValueError):
            month_periods("2026-02", "2025-11")

    def test_presence_summary_separates_leading_internal_and_trailing_gaps(self) -> None:
        scanned = month_periods("2025-01", "2025-08")
        summary = summarize_presence(
            symbol="HYPEUSDT",
            dataset="klines",
            interval="15m",
            scanned_months=scanned,
            available_months=("2025-03", "2025-04", "2025-06"),
        )
        self.assertEqual(summary.first_available_month, "2025-03")
        self.assertEqual(summary.last_available_month, "2025-06")
        self.assertEqual(summary.leading_no_data_months, ("2025-01", "2025-02"))
        self.assertEqual(summary.internal_gap_months, ("2025-05",))
        self.assertEqual(summary.trailing_no_data_months, ("2025-07", "2025-08"))
        self.assertFalse(summary.contiguous_between_first_last)

    def test_contiguous_series_passes(self) -> None:
        scanned = month_periods("2025-01", "2025-06")
        summary = summarize_presence(
            symbol="BTCUSDT",
            dataset="klines",
            interval="1h",
            scanned_months=scanned,
            available_months=("2025-02", "2025-03", "2025-04", "2025-05"),
        )
        self.assertTrue(summary.contiguous_between_first_last)
        self.assertEqual(summary.leading_no_data_months, ("2025-01",))
        self.assertEqual(summary.trailing_no_data_months, ("2025-06",))

    def test_no_available_months_is_not_contiguous_authority(self) -> None:
        scanned = month_periods("2025-01", "2025-03")
        summary = summarize_presence(
            symbol="NEWUSDT",
            dataset="klines",
            interval="4h",
            scanned_months=scanned,
            available_months=(),
        )
        self.assertIsNone(summary.first_available_month)
        self.assertFalse(summary.contiguous_between_first_last)
        self.assertEqual(summary.leading_no_data_months, scanned)


if __name__ == "__main__":
    unittest.main()
