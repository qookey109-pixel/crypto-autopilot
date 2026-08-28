from __future__ import annotations

import math
import unittest

from crypto_autopilot.research.context import (
    ContextObservation,
    ResearchContextError,
    summarize_context,
    validate_context_observation,
)


def observation(*, as_of_ms: int = 1_000) -> ContextObservation:
    return ContextObservation.from_mapping(
        source_id="capafy_btc_cycle_radar",
        symbol="BTCUSDT",
        horizon="weekly",
        as_of_ms=as_of_ms,
        source_urls=("https://capafy.ai/zh-hant/agent/btc",),
        values={"health_score": 0.7, "fear_greed": None},
    )


class ResearchContextTests(unittest.TestCase):
    def test_observation_is_deterministic_and_summary_is_descriptive(self) -> None:
        item = observation()
        validate_context_observation(item)
        result = summarize_context([item], as_of_ms=2_000)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["fields_available"], ["health_score"])
        self.assertIsNone(result["composite_score"])
        self.assertFalse(result["direct_trade_trigger_authorized"])
        self.assertFalse(result["live_trading_authorized"])

    def test_future_and_invalid_values_fail_closed(self) -> None:
        with self.assertRaisesRegex(ResearchContextError, "future"):
            summarize_context([observation(as_of_ms=2_001)], as_of_ms=2_000)
        with self.assertRaisesRegex(ResearchContextError, "finite"):
            validate_context_observation(
                ContextObservation.from_mapping(
                    source_id="source",
                    symbol="BTCUSDT",
                    horizon="daily",
                    as_of_ms=1,
                    source_urls=("https://example.test/source",),
                    values={"score": math.inf},
                )
            )

    def test_unavailable_context_cannot_contain_fabricated_numbers(self) -> None:
        with self.assertRaisesRegex(ResearchContextError, "UNAVAILABLE"):
            validate_context_observation(
                ContextObservation.from_mapping(
                    source_id="source",
                    symbol="BTCUSDT",
                    horizon="daily",
                    as_of_ms=1,
                    source_urls=("https://example.test/source",),
                    values={"score": 0.0},
                    freshness_status="UNAVAILABLE",
                )
            )


if __name__ == "__main__":
    unittest.main()
