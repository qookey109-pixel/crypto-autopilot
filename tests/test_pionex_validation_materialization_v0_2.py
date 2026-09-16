import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crypto_autopilot.history.pionex_validation_materialization_v0_1 import (
    PartitionResult,
    ValidationMaterializationRejected,
)
from crypto_autopilot.history.pionex_validation_materialization_v0_2 import (
    aggregate_complete_weeks,
    validate_overlay,
    weekly_from_native_daily,
)
from crypto_autopilot.models import Candle

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "config/pionex_validation_dataset_v0_1.json"
OVERLAY_CONFIG = ROOT / "config/pionex_validation_materialization_v0_2.json"
BASE_SHA256 = "83972be4bd6bd04d264a1f136283c5b95cb5e200c86cf22be4f02664d0035cbc"
DAY_MS = 24 * 60 * 60 * 1000


def stamp(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)


def daily_rows(start: datetime, count: int) -> list[Candle]:
    rows = []
    for index in range(count):
        when = start + timedelta(days=index)
        base = 100.0 + index
        rows.append(
            Candle(
                time_ms=int(when.timestamp() * 1000),
                open=base,
                high=base + 5.0,
                low=base - 3.0,
                close=base + 2.0,
                volume=10.0 + index,
            )
        )
    return rows


class PionexValidationMaterializationV02Tests(unittest.TestCase):
    def test_frozen_v01_config_bytes_are_unchanged(self) -> None:
        self.assertEqual(hashlib.sha256(BASE_CONFIG.read_bytes()).hexdigest(), BASE_SHA256)

    def test_overlay_is_fail_closed_and_binds_frozen_v01(self) -> None:
        overlay = json.loads(OVERLAY_CONFIG.read_text())
        validate_overlay(overlay)
        self.assertFalse(overlay["authority"]["execution_authorized"])
        self.assertFalse(overlay["weekly_materialization"]["provider_splicing_allowed"])
        self.assertFalse(overlay["weekly_materialization"]["silent_interpolation_allowed"])
        self.assertEqual(overlay["weekly_materialization"]["physical_provider_interval"], "1D")
        self.assertEqual(overlay["weekly_materialization"]["logical_interval"], "1W")

    def test_monday_to_sunday_aggregates_exact_ohlcv(self) -> None:
        rows = daily_rows(datetime(2026, 8, 17, tzinfo=timezone.utc), 7)
        result = aggregate_complete_weeks(rows)
        self.assertEqual(len(result.candles), 1)
        weekly = result.candles[0]
        self.assertEqual(weekly.time_ms, stamp(2026, 8, 17))
        self.assertEqual(weekly.open, rows[0].open)
        self.assertEqual(weekly.high, max(row.high for row in rows))
        self.assertEqual(weekly.low, min(row.low for row in rows))
        self.assertEqual(weekly.close, rows[-1].close)
        self.assertEqual(weekly.volume, sum(row.volume for row in rows))
        self.assertEqual(result.source_rows_used, 7)

    def test_partial_edge_weeks_are_not_emitted(self) -> None:
        rows = daily_rows(datetime(2026, 8, 14, tzinfo=timezone.utc), 14)
        result = aggregate_complete_weeks(rows)
        self.assertEqual([row.time_ms for row in result.candles], [stamp(2026, 8, 17)])
        self.assertEqual(result.dropped_leading_rows, 3)
        self.assertEqual(result.dropped_trailing_rows, 4)
        self.assertEqual(result.source_rows_used, 7)

    def test_gap_or_duplicate_fails_closed(self) -> None:
        rows = daily_rows(datetime(2026, 8, 17, tzinfo=timezone.utc), 7)
        with self.assertRaises(ValidationMaterializationRejected):
            aggregate_complete_weeks(rows[:3] + rows[4:])
        with self.assertRaises(ValidationMaterializationRejected):
            aggregate_complete_weeks(rows[:3] + [rows[2]] + rows[3:])

    def test_weekly_partition_reuses_native_daily_requests_and_lineage(self) -> None:
        base_config = json.loads(BASE_CONFIG.read_text())
        rows = tuple(daily_rows(datetime(2026, 8, 17, tzinfo=timezone.utc), 7))
        source = PartitionResult(
            symbol="BTC_USDT_PERP",
            interval="1D",
            coverage_status="PROVIDER_EARLIEST_REACHED",
            candles=rows,
            requests=4,
        )
        result = weekly_from_native_daily(base_config, symbol="BTC_USDT_PERP", source_daily_result=source)
        receipt = result.receipt_fields()
        self.assertEqual(result.requests, 0)
        self.assertEqual(receipt["logical_interval"], "1W")
        self.assertEqual(receipt["physical_provider_interval"], "1D")
        self.assertTrue(receipt["physical_requests_reused_from_source_partition"])
        self.assertEqual(receipt["physical_provider_requests_reused"], 4)
        self.assertFalse(receipt["complete_provider_history_claimed"])

    def test_week_alignment_matches_project_monday_utc_contract(self) -> None:
        rows = daily_rows(datetime(2026, 8, 17, tzinfo=timezone.utc), 14)
        result = aggregate_complete_weeks(rows)
        self.assertEqual(
            [row.time_ms for row in result.candles],
            [stamp(2026, 8, 17), stamp(2026, 8, 24)],
        )
        self.assertEqual(result.candles[1].time_ms - result.candles[0].time_ms, 7 * DAY_MS)


if __name__ == "__main__":
    unittest.main()
