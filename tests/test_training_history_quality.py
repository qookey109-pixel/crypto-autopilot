from __future__ import annotations

import unittest
from datetime import UTC, datetime

from crypto_autopilot.models import Candle
from crypto_autopilot.training.history_quality import (
    LIFECYCLE_GAP_CLASSIFICATION,
    STRICT_AUDIT_PASS,
    VERIFIED_RECONCILIATION,
    TrainingHistoryQualityError,
    candidate_sha256,
    validate_training_partition,
)


def candle(time_ms: int, close: float = 100.0) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close + 0.25,
        volume=10.0,
    )


def contiguous(step: int, count: int, *, start: int = 0) -> tuple[Candle, ...]:
    return tuple(candle(start + index * step, 100.0 + index * 0.01) for index in range(count))


class TrainingHistoryQualityTests(unittest.TestCase):
    def test_strict_binance_partition_is_reaudited(self) -> None:
        rows = contiguous(900_000, 4)
        record = {
            "provider": "binance_usdm",
            "delivery": "binance_vision",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "period": "2025-01",
            "source_rows": len(rows),
            "source_archive_sha256": "a" * 64,
            "audit_ok": True,
        }
        self.assertEqual(validate_training_partition(record, rows), STRICT_AUDIT_PASS)
        broken = (rows[0], rows[2], rows[3])
        record["source_rows"] = len(broken)
        with self.assertRaisesRegex(TrainingHistoryQualityError, "strict.*audit"):
            validate_training_partition(record, broken)

    def test_exact_ctk_lifecycle_gap_is_accepted_without_filling(self) -> None:
        step = 900_000
        start = int(datetime(2025, 4, 1, tzinfo=UTC).timestamp() * 1000)
        end = int(datetime(2025, 5, 1, tzinfo=UTC).timestamp() * 1000)
        gap_start = int(datetime(2025, 4, 30, tzinfo=UTC).timestamp() * 1000)
        gap_end = int(datetime(2025, 4, 30, 10, 15, tzinfo=UTC).timestamp() * 1000)
        rows = tuple(
            candle(stamp, 100.0 + index * 0.0001)
            for index, stamp in enumerate(range(start, end, step))
            if not gap_start <= stamp < gap_end
        )
        self.assertEqual(len(rows), 2839)
        record = {
            "provider": "binance_usdm",
            "delivery": "binance_vision",
            "symbol": "CTKUSDT",
            "interval": "15m",
            "period": "2025-04",
            "source_rows": 2839,
            "source_archive_sha256": "bd77c44d0061511b2e8f5c140a06ad2dd30007c640586fad5b035d71b0c3c61c",
            "audit_ok": False,
        }
        self.assertEqual(
            validate_training_partition(record, rows), LIFECYCLE_GAP_CLASSIFICATION
        )
        record["source_archive_sha256"] = "0" * 64
        with self.assertRaisesRegex(TrainingHistoryQualityError, "unreviewed.*gap"):
            validate_training_partition(record, rows)

    def test_verified_bnx_reconciliation_recomputes_candidate_hash(self) -> None:
        rows = contiguous(3_600_000, 8)
        monthly_sha = "b" * 64
        record = {
            "provider": "binance_usdm",
            "delivery": "binance_vision_monthly_daily_reconciliation",
            "symbol": "BNXUSDT",
            "interval": "1h",
            "period": "2022-08",
            "source_rows": len(rows),
            "source_archive_sha256": monthly_sha,
            "audit_ok": True,
            "repair_lineage": {
                "schema": "bnx-archive-repair-lineage-v0.2",
                "provider": "binance_usdm",
                "monthly_sha256": monthly_sha,
                "original_monthly_rows": 6,
                "original_monthly_audit_ok": False,
                "original_monthly_archive_regraded": False,
                "candidate_rows": len(rows),
                "candidate_sha256": candidate_sha256(rows),
            },
        }
        self.assertEqual(validate_training_partition(record, rows), VERIFIED_RECONCILIATION)
        record["repair_lineage"]["candidate_sha256"] = "0" * 64
        with self.assertRaisesRegex(TrainingHistoryQualityError, "candidate SHA"):
            validate_training_partition(record, rows)

    def test_unknown_delivery_remains_fail_closed(self) -> None:
        rows = contiguous(900_000, 2)
        record = {
            "provider": "binance_usdm",
            "delivery": "unknown",
            "symbol": "BTCUSDT",
            "interval": "15m",
            "period": "2025-01",
            "source_rows": len(rows),
            "source_archive_sha256": "a" * 64,
            "audit_ok": True,
        }
        with self.assertRaisesRegex(TrainingHistoryQualityError, "delivery"):
            validate_training_partition(record, rows)


if __name__ == "__main__":
    unittest.main()
