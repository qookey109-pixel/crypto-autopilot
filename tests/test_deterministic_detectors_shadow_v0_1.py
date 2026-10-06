from __future__ import annotations

import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.prospective_shadow_test_v0_1 import (
    build_shadow_signal_record,
    evaluate_shadow_outcomes,
)
from crypto_autopilot.research.technical_pattern_detectors_v0_1 import (
    ConfirmedPivot,
    DetectorPolicy,
    build_technical_pattern_series,
    classify_harmonic_pattern,
)
from crypto_autopilot.technical import TechnicalSnapshot

STEP = 15 * 60 * 1000


def candle(
    index: int,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 100.0,
) -> Candle:
    return Candle(index * STEP, open_, high, low, close, volume)


def technical(index: int, macd_histogram: float) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        bar_time_ms=index * STEP,
        available_at_ms=(index + 1) * STEP,
        close=100.0,
        volume=100.0,
        ema20=None,
        ema50=None,
        ema20_slope=None,
        atr14=None,
        volume_sma20=None,
        volume_ratio=None,
        previous_high=None,
        extension_from_ema20_atr=None,
        macd_histogram=macd_histogram,
    )


class DeterministicDetectorV01Tests(unittest.TestCase):
    def test_liquidity_sweep_and_fvg_are_deterministic(self) -> None:
        candles = [
            candle(i, open_=100, high=101, low=99, close=100)
            for i in range(20)
        ]
        candles.append(candle(20, open_=100, high=103, low=100, close=101))
        candles.append(candle(21, open_=101, high=102, low=100.8, close=101.8))
        candles.append(candle(22, open_=103.5, high=104, low=103.5, close=103.8))

        series = build_technical_pattern_series(
            candles,
            "15M",
            policy=DetectorPolicy(swing_left=1, swing_right=1),
        )
        self.assertEqual(series[20].liquidity_event, "HIGH_SWEEP_RECLAIM")
        self.assertEqual(series[22].fvg_bias, "BULLISH")
        self.assertEqual(series[22].fvg_zone_low, 103.0)
        self.assertEqual(series[22].fvg_zone_high, 103.5)

    def test_order_block_requires_displacement_and_opposite_previous_candle(self) -> None:
        candles = [
            candle(i, open_=100, high=101, low=99, close=100.2)
            for i in range(10)
        ]
        candles.append(candle(10, open_=100.5, high=101, low=99.5, close=100.0))
        candles.append(candle(11, open_=100.0, high=104, low=99.8, close=103.8))

        series = build_technical_pattern_series(
            candles,
            "15M",
            policy=DetectorPolicy(
                liquidity_lookback=5,
                order_block_lookback=10,
                order_block_body_fraction_floor=0.6,
                swing_left=1,
                swing_right=1,
            ),
        )
        self.assertEqual(series[11].order_block_bias, "BULLISH")
        self.assertEqual(series[11].order_block_zone_low, 99.5)
        self.assertEqual(series[11].order_block_zone_high, 101.0)

    def test_gartley_ratio_candidate_is_location_evidence(self) -> None:
        pivots = [
            ConfirmedPivot(0, "LOW", 80.0),
            ConfirmedPivot(1, "HIGH", 100.0),
            ConfirmedPivot(2, "LOW", 87.64),
            ConfirmedPivot(3, "HIGH", 93.82),
            ConfirmedPivot(4, "LOW", 84.28),
        ]
        self.assertEqual(
            classify_harmonic_pattern(pivots),
            ("GARTLEY", "BULLISH"),
        )

    def test_macd_bullish_divergence_uses_confirmed_price_lows(self) -> None:
        lows = [10, 9, 7, 9, 10, 8, 6, 8, 9]
        candles = [
            candle(
                i,
                open_=low + 1,
                high=low + 2,
                low=low,
                close=low + 1,
            )
            for i, low in enumerate(lows)
        ]
        hist = [0.0, -1.0, -2.0, -1.0, 0.0, -0.5, -1.0, -0.5, 0.0]
        technical_series = [
            technical(i, value)
            for i, value in enumerate(hist)
        ]
        series = build_technical_pattern_series(
            candles,
            "15M",
            technical_series=technical_series,
            policy=DetectorPolicy(
                liquidity_lookback=5,
                order_block_lookback=5,
                swing_left=1,
                swing_right=1,
            ),
        )
        self.assertEqual(series[7].macd_divergence, "BULLISH")


class ProspectiveShadowV01Tests(unittest.TestCase):
    def test_signal_freezes_latency_and_outcomes_use_exact_horizons(self) -> None:
        signal = build_shadow_signal_record(
            symbol="BTCUSDT",
            as_of_ms=0,
            reference_price=100.0,
            qookey_candidate={"score": 72.0, "direction": "LONG"},
            router_result="NO_TRADE",
            qookey_detected_at_ms=0,
            event_observed_at_ms=0,
            comparison_signal="fixture",
            comparison_direction="LONG",
            comparison_detected_at_ms=0,
        )
        candles = []
        for index in range(96):
            close = 100.0 - (index + 1) * 0.01
            candles.append(
                candle(
                    index,
                    open_=close,
                    high=close + 0.2,
                    low=close - 0.2,
                    close=close,
                )
            )

        outcome = evaluate_shadow_outcomes(
            signal=signal,
            candles=candles,
            interval="15M",
            evaluated_at_ms=24 * 60 * 60 * 1000,
        )
        self.assertEqual(outcome["horizons"]["1H"]["status"], "OBSERVED")
        self.assertEqual(outcome["horizons"]["24H"]["status"], "OBSERVED")
        self.assertLess(outcome["horizons"]["24H"]["return"], 0.0)
        self.assertEqual(outcome["no_trade_quality_24h"], "AVOIDED_LOSS")

    def test_future_horizon_is_not_evaluated_early(self) -> None:
        signal = build_shadow_signal_record(
            symbol="BTCUSDT",
            as_of_ms=0,
            reference_price=100.0,
            qookey_candidate={"score": 70.0},
            router_result="ROUTES_READY",
        )
        self.assertEqual(signal["router_status"], "ROUTES_READY")
        self.assertEqual(signal["router_result"], "MATCH")
        candles = [
            candle(i, open_=100, high=101, low=99, close=100)
            for i in range(4)
        ]
        outcome = evaluate_shadow_outcomes(
            signal=signal,
            candles=candles,
            interval="15M",
            evaluated_at_ms=60 * 60 * 1000,
        )
        self.assertEqual(outcome["horizons"]["1H"]["status"], "OBSERVED")
        self.assertEqual(outcome["horizons"]["4H"]["status"], "NOT_YET_AVAILABLE")

    def test_modified_frozen_signal_fails_integrity_check(self) -> None:
        signal = build_shadow_signal_record(
            symbol="BTCUSDT",
            as_of_ms=0,
            reference_price=100.0,
            qookey_candidate={"score": 70.0},
            router_result="NO_TRADE",
        )
        signal["reference_price"] = 101.0
        with self.assertRaises(ValueError):
            evaluate_shadow_outcomes(
                signal=signal,
                candles=[
                    candle(i, open_=100, high=101, low=99, close=100)
                    for i in range(4)
                ],
                interval="15M",
                evaluated_at_ms=60 * 60 * 1000,
            )


if __name__ == "__main__":
    unittest.main()
