from __future__ import annotations

import unittest
from datetime import date

from crypto_autopilot.binance.coverage import (
    attach_audited_boundaries,
    build_archive_keys,
    daily_periods,
    month_periods,
    summarize_presence,
    summarize_symbol_boundaries,
)


class BinanceCoverageTests(unittest.TestCase):
    def test_month_periods_cross_year(self) -> None:
        self.assertEqual(
            month_periods("2025-11", "2026-02"),
            ("2025-11", "2025-12", "2026-01", "2026-02"),
        )

    def test_daily_periods_empty_when_end_precedes_start(self) -> None:
        self.assertEqual(daily_periods(date(2026, 8, 1), date(2026, 7, 31)), ())

    def test_build_archive_keys_keeps_frozen_four_series(self) -> None:
        keys = build_archive_keys(
            ("BTCUSDT",),
            frequency="monthly",
            periods=("2026-06", "2026-07"),
        )
        self.assertEqual(len(keys), 8)
        self.assertEqual(
            {(key.dataset, key.interval) for key in keys},
            {
                ("klines", "15m"),
                ("klines", "1h"),
                ("klines", "4h"),
                ("markPriceKlines", "1h"),
            },
        )

    def test_presence_records_internal_gaps_without_inventing_data(self) -> None:
        periods = ("2025-01", "2025-02", "2025-03", "2025-04")
        records = [
            {
                "symbol": "BTCUSDT",
                "dataset": "klines",
                "interval": "15m",
                "period": period,
                "status": status,
            }
            for period, status in zip(
                periods,
                ("NO_DATA", "AVAILABLE", "NO_DATA", "AVAILABLE"),
                strict=True,
            )
        ]
        summary = summarize_presence(
            records,
            symbol="BTCUSDT",
            dataset="klines",
            interval="15m",
            ordered_periods=periods,
        )
        self.assertEqual(summary["first_available_period"], "2025-02")
        self.assertEqual(summary["last_available_period"], "2025-04")
        self.assertEqual(summary["missing_periods_within_observed_span"], ["2025-03"])
        self.assertFalse(summary["continuous_archive_presence_within_observed_span"])

    def test_audited_daily_edge_extends_latest_without_changing_earliest(self) -> None:
        summary = {
            "symbol": "BTCUSDT",
            "dataset": "klines",
            "interval": "15m",
            "missing_periods_within_observed_span": [],
        }
        first = {"first_time_ms": 1_735_689_600_000, "last_time_ms": 1_735_690_500_000}
        last = {"first_time_ms": 1_751_328_000_000, "last_time_ms": 1_753_977_500_000}
        daily = {"first_time_ms": 1_754_006_400_000, "last_time_ms": 1_754_092_700_000}
        attached = attach_audited_boundaries(
            summary,
            first_receipt=first,
            last_receipt=last,
            latest_daily_receipt=daily,
        )
        self.assertEqual(attached["earliest_candle_time_ms"], first["first_time_ms"])
        self.assertEqual(attached["latest_candle_time_ms"], daily["last_time_ms"])

    def test_symbol_common_window_uses_narrowest_required_series(self) -> None:
        def series(dataset: str, interval: str, earliest: int, latest: int) -> dict[str, object]:
            return {
                "symbol": "BTCUSDT",
                "dataset": dataset,
                "interval": interval,
                "earliest_candle_time_ms": earliest,
                "latest_candle_time_ms": latest,
                "missing_periods_within_observed_span": [],
            }

        summaries = [
            series("klines", "15m", 100, 1_000),
            series("klines", "1h", 120, 950),
            series("klines", "4h", 90, 900),
            series("markPriceKlines", "1h", 130, 880),
        ]
        result = summarize_symbol_boundaries("BTCUSDT", summaries)
        self.assertEqual(result["trade_common_window"]["earliest_candle_time_ms"], 120)
        self.assertEqual(result["trade_common_window"]["latest_candle_time_ms"], 900)
        self.assertEqual(
            result["strategy_price_common_window"]["earliest_candle_time_ms"],
            130,
        )
        self.assertEqual(
            result["strategy_price_common_window"]["latest_candle_time_ms"],
            880,
        )


if __name__ == "__main__":
    unittest.main()
