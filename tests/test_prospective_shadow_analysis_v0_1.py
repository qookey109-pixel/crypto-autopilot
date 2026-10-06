from __future__ import annotations

import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.prospective_shadow_analysis_v0_1 import (
    aggregate_shadow_records,
)
from crypto_autopilot.research.prospective_shadow_test_v0_1 import (
    build_shadow_signal_record,
    evaluate_shadow_outcomes,
)

STEP = 15 * 60 * 1000
DAY = 24 * 60 * 60 * 1000


def outcome_for(
    signal: dict[str, object],
    *,
    rising: bool,
) -> dict[str, object]:
    as_of_ms = int(signal["as_of_ms"])
    candles = []
    for index in range(96):
        change = (index + 1) * 0.01
        close = 100.0 + change if rising else 100.0 - change
        candles.append(
            Candle(
                time_ms=as_of_ms + index * STEP,
                open=close,
                high=close + 0.2,
                low=close - 0.2,
                close=close,
                volume=100.0,
            )
        )
    return evaluate_shadow_outcomes(
        signal=signal,
        candles=candles,
        interval="15M",
        evaluated_at_ms=as_of_ms + DAY,
    )


class ProspectiveShadowAnalysisV01Tests(unittest.TestCase):
    def test_aggregates_review_window_expectancy_and_no_trade_quality(self) -> None:
        first = build_shadow_signal_record(
            symbol="BTCUSDT",
            as_of_ms=0,
            reference_price=100.0,
            qookey_candidate={"score": 80.0, "direction": "LONG"},
            router_result="ROUTES_READY",
            event_observed_at_ms=0,
            qookey_detected_at_ms=0,
            comparison_signal="fixture",
            comparison_direction="SHORT",
            comparison_detected_at_ms=0,
        )
        second = build_shadow_signal_record(
            symbol="ETHUSDT",
            as_of_ms=31 * DAY,
            reference_price=100.0,
            qookey_candidate={"score": 78.0, "bias": "SHORT_BIAS"},
            router_result="ROUTES_READY",
            comparison_signal="fixture",
            comparison_direction="LONG",
        )
        third = build_shadow_signal_record(
            symbol="SOLUSDT",
            as_of_ms=60 * DAY,
            reference_price=100.0,
            qookey_candidate={"score": 65.0, "bias": "NEUTRAL"},
            router_result="NO_TRADE",
            comparison_signal="fixture",
            comparison_direction="LONG",
        )

        analysis = aggregate_shadow_records(
            [
                {"signal": first, "outcome": outcome_for(first, rising=True)},
                {"signal": second, "outcome": outcome_for(second, rising=False)},
                {"signal": third, "outcome": outcome_for(third, rising=False)},
            ]
        )

        self.assertEqual(analysis["record_count"], 3)
        self.assertEqual(analysis["collection_status"], "REVIEW_WINDOW")
        self.assertEqual(analysis["prospective_span_days"], 60.0)
        qookey_24h = analysis["horizons"]["24H"]["qookey"]
        comparison_24h = analysis["horizons"]["24H"]["comparison"]
        self.assertEqual(qookey_24h["sample_count"], 2)
        self.assertEqual(qookey_24h["win_rate"], 1.0)
        self.assertGreater(qookey_24h["expectancy"], 0.0)
        self.assertEqual(comparison_24h["sample_count"], 3)
        self.assertLess(comparison_24h["expectancy"], 0.0)
        self.assertEqual(
            analysis["no_trade_quality_24h"]["AVOIDED_LOSS"],
            1,
        )
        self.assertFalse(
            analysis["interpretation"]["automatic_winner_selection"]
        )

    def test_under_30_days_remains_collecting(self) -> None:
        signal = build_shadow_signal_record(
            symbol="BTCUSDT",
            as_of_ms=0,
            reference_price=100.0,
            qookey_candidate={"score": 70.0, "direction": "LONG"},
            router_result="ROUTES_READY",
        )
        analysis = aggregate_shadow_records(
            [{"signal": signal, "outcome": outcome_for(signal, rising=True)}]
        )
        self.assertEqual(analysis["collection_status"], "COLLECTING")
        self.assertEqual(analysis["prospective_span_days"], 0.0)

    def test_duplicate_signal_fails_closed(self) -> None:
        signal = build_shadow_signal_record(
            symbol="BTCUSDT",
            as_of_ms=0,
            reference_price=100.0,
            qookey_candidate={"score": 70.0, "direction": "LONG"},
            router_result="ROUTES_READY",
        )
        pair = {"signal": signal, "outcome": outcome_for(signal, rising=True)}
        with self.assertRaises(ValueError):
            aggregate_shadow_records([pair, pair])

    def test_empty_analysis_has_no_promotion_semantics(self) -> None:
        analysis = aggregate_shadow_records([])
        self.assertEqual(analysis["collection_status"], "NO_RECORDS")
        self.assertEqual(analysis["record_count"], 0)
        self.assertFalse(
            analysis["interpretation"]["automatic_model_promotion"]
        )


if __name__ == "__main__":
    unittest.main()
