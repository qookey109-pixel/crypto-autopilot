from __future__ import annotations

import unittest

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.history.pionex_gap_boundary_v0_1 import (
    GapBoundaryKlineClient,
    PionexInternalGapBoundary,
)
from crypto_autopilot.models import Candle


def candle(time_ms: int, *, high: float = 101.0, close: float = 100.5) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=100.0,
        high=high,
        low=99.0,
        close=close,
        volume=10.0,
    )


class StaticClient:
    def __init__(self, rows: list[Candle]) -> None:
        self.rows = rows

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        return list(self.rows)


class PionexGapBoundaryTests(unittest.TestCase):
    def test_gap_only_page_becomes_provider_boundary(self) -> None:
        step = INTERVAL_MS["4H"]
        client = GapBoundaryKlineClient(
            StaticClient([candle(0), candle(step), candle(step * 3)])
        )
        with self.assertRaises(PionexInternalGapBoundary):
            client.get_klines(
                "AAVE_USDT_PERP",
                "4H",
                limit=500,
                end_time_ms=step * 3,
            )

    def test_contiguous_page_passes_through_unchanged(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [candle(0), candle(step), candle(step * 2)]
        client = GapBoundaryKlineClient(StaticClient(rows))
        self.assertEqual(
            client.get_klines(
                "AAVE_USDT_PERP",
                "4H",
                limit=500,
                end_time_ms=step * 2,
            ),
            rows,
        )

    def test_non_gap_defect_is_left_for_core_fail_closed_validation(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [candle(0, high=100.0, close=102.0), candle(step)]
        client = GapBoundaryKlineClient(StaticClient(rows))
        self.assertEqual(
            client.get_klines(
                "AAVE_USDT_PERP",
                "4H",
                limit=500,
                end_time_ms=step,
            ),
            rows,
        )


if __name__ == "__main__":
    unittest.main()
