from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace

from crypto_autopilot.research_signal_layer import (
    ClosedCandleRecord,
    KOLForecast,
    ResearchSignalLayerError,
    append_closed_candles,
    deduplicate_kol_forecasts,
    evaluate_kol_forecasts,
)


def candle(*, close_time_ms: int = 2_000) -> ClosedCandleRecord:
    return ClosedCandleRecord(
        provider="binance_spot",
        symbol="BTCUSDT",
        interval="15m",
        open_time_ms=1_000,
        close_time_ms=close_time_ms,
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
        volume=10.0,
    )


def forecast(*, forecast_id: str = "f-1", target_time_ms: int = 3_000) -> KOLForecast:
    return KOLForecast(
        forecast_id=forecast_id,
        source="example-kol",
        source_url="https://example.test/post/1",
        symbol="BTCUSDT",
        direction="long",
        confidence=0.8,
        published_at_ms=1_500,
        target_time_ms=target_time_ms,
        ingested_at_ms=1_600,
        content_sha256=hashlib.sha256(b"forecast").hexdigest(),
    )


class ResearchSignalLayerTests(unittest.TestCase):
    def test_closed_candles_append_is_sorted_and_idempotent(self) -> None:
        later = replace(candle(), open_time_ms=3_000, close_time_ms=4_000)
        merged = append_closed_candles(
            [later], [candle(), candle()], provider="binance_spot", ingested_at_ms=5_000
        )
        self.assertEqual([item.open_time_ms for item in merged], [1_000, 3_000])

    def test_open_candle_and_provider_mixing_fail_closed(self) -> None:
        with self.assertRaisesRegex(ResearchSignalLayerError, "not closed"):
            append_closed_candles([], [candle(close_time_ms=6_000)], provider="binance_spot", ingested_at_ms=5_000)
        other = replace(candle(), provider="pionex_public_futures")
        with self.assertRaisesRegex(ResearchSignalLayerError, "provider stream mixing"):
            append_closed_candles([], [other], provider="binance_spot", ingested_at_ms=5_000)

    def test_conflicting_candle_revision_is_rejected(self) -> None:
        revised = replace(candle(), close=103.0)
        with self.assertRaisesRegex(ResearchSignalLayerError, "revision"):
            append_closed_candles([candle()], [revised], provider="binance_spot", ingested_at_ms=5_000)

    def test_kol_forecast_requires_time_safe_https_lineage(self) -> None:
        with self.assertRaisesRegex(ResearchSignalLayerError, "HTTPS"):
            deduplicate_kol_forecasts(
                [], [replace(forecast(), source_url="http://bad.test")]
            )

    def test_kol_duplicate_is_idempotent_and_revision_rejected(self) -> None:
        item = forecast()
        self.assertEqual(deduplicate_kol_forecasts([item], [item]), (item,))
        revised = replace(item, confidence=0.7)
        with self.assertRaisesRegex(ResearchSignalLayerError, "revision"):
            deduplicate_kol_forecasts([item], [revised])

    def test_kol_evaluation_excludes_unrealized_outcomes_and_has_no_authority(self) -> None:
        first = forecast()
        second = forecast(forecast_id="f-2", target_time_ms=4_000)
        result = evaluate_kol_forecasts(
            [first, second],
            {"f-1": (3_100, 0.02), "f-2": (4_100, -0.01)},
            as_of_ms=3_500,
        )
        self.assertEqual(result["status"], "EVALUATED")
        self.assertEqual(result["evaluated_count"], 1)
        self.assertEqual(result["accuracy"], 1.0)
        self.assertFalse(result["automatic_model_promotion_authorized"])
        self.assertFalse(result["direct_trade_trigger_authorized"])

    def test_kol_not_ready_before_target_time(self) -> None:
        result = evaluate_kol_forecasts([forecast()], {}, as_of_ms=2_999)
        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["evaluated_count"], 0)


if __name__ == "__main__":
    unittest.main()
