from __future__ import annotations

import unittest

from crypto_autopilot.features.orderflow import (
    OrderFlowDataError,
    build_spot_orderflow_series,
)


def rows(count: int = 30) -> list[dict[str, float]]:
    return [
        {
            "base_volume": 100.0 + index,
            "quote_volume": 1_000.0 + index * 10.0,
            "taker_buy_base_volume": 45.0 + index * 0.6,
            "taker_buy_quote_volume": 450.0 + index * 4.5,
        }
        for index in range(count)
    ]


class OrderFlowTests(unittest.TestCase):
    def test_builds_causal_buy_ratio_delta_zscore_and_cvd(self) -> None:
        source = rows()
        baseline = build_spot_orderflow_series(source)
        self.assertTrue(baseline[-1].ready)
        self.assertAlmostEqual(baseline[-1].taker_buy_ratio or 0.0, 0.45)
        self.assertLess(baseline[-1].buy_sell_quote_volume_delta or 0.0, 0.0)
        self.assertIsNotNone(baseline[-1].taker_buy_volume_zscore20)
        self.assertIsNotNone(baseline[-1].rolling_cvd20_fraction)

        changed_rows = rows()
        changed_rows[-1]["taker_buy_quote_volume"] = 900.0
        changed = build_spot_orderflow_series(changed_rows)
        self.assertEqual(baseline[:-1], changed[:-1])
        self.assertNotEqual(baseline[-1], changed[-1])

    def test_legacy_missing_fields_remain_explicitly_unavailable(self) -> None:
        snapshot = build_spot_orderflow_series(
            [{"base_volume": 1.0, "quote_volume": 100.0}] * 20
        )[-1]
        self.assertFalse(snapshot.ready)
        self.assertTrue(
            all(value is None for value in snapshot.normalized_features.values())
        )

    def test_partial_or_out_of_bounds_taker_data_fails_closed(self) -> None:
        with self.assertRaisesRegex(OrderFlowDataError, "paired"):
            build_spot_orderflow_series(
                [
                    {
                        "base_volume": 10.0,
                        "quote_volume": 100.0,
                        "taker_buy_base_volume": 5.0,
                    }
                ]
            )
        with self.assertRaisesRegex(OrderFlowDataError, "exceeds"):
            build_spot_orderflow_series(
                [
                    {
                        "base_volume": 10.0,
                        "quote_volume": 100.0,
                        "taker_buy_base_volume": 5.0,
                        "taker_buy_quote_volume": 120.0,
                    }
                ]
            )


if __name__ == "__main__":
    unittest.main()
