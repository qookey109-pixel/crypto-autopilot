from __future__ import annotations

import math
import unittest

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.history.pionex_gap_boundary_v0_1 import (
    GapBoundaryKlineClient,
    PionexInternalGapBoundary,
    PionexInvalidCandleBoundary,
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

    def test_bounds_only_invalid_page_returns_clean_newer_suffix(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [
            candle(0),
            candle(step, low=100.75, close=100.5),
            candle(step * 2),
            candle(step * 3),
        ]
        client = GapBoundaryKlineClient(StaticClient(rows))
        self.assertEqual(
            client.get_klines(
                "AAVE_USDT_PERP",
                "4H",
                limit=500,
                end_time_ms=step * 3,
            ),
            rows[2:],
        )

    def test_bounds_only_invalid_probe_becomes_provider_boundary(self) -> None:
        step = INTERVAL_MS["4H"]
        client = GapBoundaryKlineClient(
            StaticClient([candle(step, high=100.0, close=100.5)])
        )
        with self.assertRaises(PionexInvalidCandleBoundary):
            client.get_klines(
                "AAVE_USDT_PERP",
                "4H",
                limit=1,
                end_time_ms=step,
            )

    def test_other_invalid_candle_types_stay_fail_closed_for_core(self) -> None:
        step = INTERVAL_MS["4H"]
        cases = {
            "nonfinite": candle(0, high=math.inf),
            "nonpositive": candle(0, open_=0.0),
            "negative_volume": candle(0, volume=-1.0),
            "inverted_range": candle(0, high=98.0, low=99.0),
        }
        for name, invalid in cases.items():
            with self.subTest(name=name):
                rows = [invalid, candle(step)]
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

    def test_bounds_invalid_plus_time_gap_stays_fail_closed_for_core(self) -> None:
        step = INTERVAL_MS["4H"]
        rows = [
            candle(0, high=100.0, close=100.5),
            candle(step * 2),
        ]
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


if __name__ == "__main__":
    unittest.main()
