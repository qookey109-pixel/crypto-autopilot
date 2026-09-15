from __future__ import annotations

import math
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
        self.assertEqual(diagnostics["invalid_high_below_ohlc_count"], 1)
        self.assertEqual(
            diagnostics["first_invalid_high_below_ohlc_timestamp_ms"],
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

    def test_classifies_invalid_reasons_without_emitting_values(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [
            candle(0, open_=0.0, low=0.0),
            candle(step, volume=-1.0),
            candle(step * 2, high=100.0, close=102.0),
            candle(step * 3, low=102.0, high=103.0, open_=100.0, close=101.0),
            candle(step * 4, high=math.inf),
        ]
        diagnostics = page_audit_diagnostics(rows, interval="4H", cursor=step * 4)

        self.assertEqual(diagnostics["invalid_candle_count"], 5)
        self.assertEqual(diagnostics["invalid_nonpositive_price_count"], 1)
        self.assertEqual(diagnostics["invalid_negative_volume_count"], 1)
        self.assertEqual(diagnostics["invalid_high_below_ohlc_count"], 1)
        self.assertEqual(diagnostics["invalid_low_above_ohlc_count"], 1)
        self.assertEqual(diagnostics["invalid_nonfinite_count"], 1)
        self.assertNotIn("open", diagnostics)
        self.assertNotIn("high", diagnostics)
        self.assertNotIn("low", diagnostics)
        self.assertNotIn("close", diagnostics)
        self.assertNotIn("volume", diagnostics)


if __name__ == "__main__":
    unittest.main()
