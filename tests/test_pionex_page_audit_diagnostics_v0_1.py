from __future__ import annotations

import unittest

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.history.pionex_page_audit_diagnostics_v0_1 import (
    page_audit_diagnostics,
)
from crypto_autopilot.models import Candle


def candle(
    time_ms: int,
    *,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: float = 10.0,
) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


class PionexPageAuditDiagnosticsTests(unittest.TestCase):
    def test_reports_gap_and_invalid_candle_separately(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [
            candle(0),
            candle(step * 2, high=100.0, close=102.0),
        ]
        diagnostics = page_audit_diagnostics(
            rows,
            interval="4H",
            cursor=step * 2,
        )
        self.assertEqual(diagnostics["gap_count"], 1)
        self.assertEqual(diagnostics["first_gap_missing_bars"], 1)
        self.assertEqual(diagnostics["invalid_candle_count"], 1)
        self.assertEqual(
            diagnostics["first_invalid_candle_timestamp_ms"],
            step * 2,
        )
        self.assertEqual(diagnostics["duplicate_timestamp_count"], 0)
        self.assertEqual(diagnostics["misaligned_timestamp_count"], 0)

    def test_reports_duplicate_and_misalignment_without_raw_payload(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [candle(1), candle(1), candle(step + 1)]
        diagnostics = page_audit_diagnostics(
            rows,
            interval="4H",
            cursor=step + 1,
        )
        self.assertEqual(diagnostics["duplicate_timestamp_count"], 1)
        self.assertEqual(diagnostics["misaligned_timestamp_count"], 2)
        self.assertEqual(diagnostics["invalid_candle_count"], 0)
        self.assertNotIn("candles", diagnostics)
        self.assertNotIn("raw_provider_payload", diagnostics)


if __name__ == "__main__":
    unittest.main()
