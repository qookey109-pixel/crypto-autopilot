from __future__ import annotations

import unittest

from crypto_autopilot.research.decision_classification_v0_1 import (
    BOUNDED_SCHEMA,
    build_bounded_decision_record,
)
from crypto_autopilot.research.market_event_radar_v0_1 import (
    build_market_event_radar_snapshot,
)
from crypto_autopilot.research.opportunity_research_adapter_v0_1 import (
    attach_research_sidecars,
)
from crypto_autopilot.research.technical_confluence_v0_1 import (
    build_technical_confluence_snapshot,
)


class ResearchSidecarsV01Tests(unittest.TestCase):
    def test_market_event_radar_is_causal_and_descriptive(self) -> None:
        snapshot = build_market_event_radar_snapshot(
            symbol="btcusdt",
            as_of_ms=1000,
            observed_at_ms=900,
            available_at_ms=950,
            features={
                "relative_volume": 1.4,
                "volume_zscore": 2.0,
                "oi_change_pct": 1.2,
                "funding_rate": 0.0001,
                "liquidation_imbalance": -0.25,
                "vwap_zscore": 1.1,
                "volatility_compression_ratio": 0.7,
                "volatility_expansion_ratio": 1.3,
                "market_breadth": 0.4,
            },
        )
        self.assertEqual(snapshot["symbol"], "BTCUSDT")
        self.assertIn("RVOL_AT_OR_ABOVE_BASELINE", snapshot["events"])
        self.assertIn("VOLATILITY_EXPANDING", snapshot["events"])
        self.assertFalse(snapshot["authority"]["opportunity_score_change_authorized"])

    def test_market_event_radar_rejects_future_evidence(self) -> None:
        with self.assertRaises(ValueError):
            build_market_event_radar_snapshot(
                symbol="BTCUSDT",
                as_of_ms=100,
                observed_at_ms=90,
                available_at_ms=101,
                features={"relative_volume": 1.0},
            )

    def test_technical_confluence_aggregates_without_entry_signal(self) -> None:
        snapshot = build_technical_confluence_snapshot(
            symbol="BTCUSDT",
            as_of_ms=1000,
            timeframes=[
                {
                    "timeframe": "4H",
                    "available_at_ms": 900,
                    "structure_state": "UP",
                    "liquidity_event": "LOW_SWEEP_RECLAIM",
                    "fvg_bias": "BULLISH",
                    "order_block_bias": "NONE",
                    "harmonic_prz": "NONE",
                    "macd_divergence": "BULLISH",
                },
                {
                    "timeframe": "1H",
                    "available_at_ms": 950,
                    "structure_state": "RANGE",
                    "liquidity_event": "NONE",
                    "fvg_bias": "NONE",
                    "order_block_bias": "NONE",
                    "harmonic_prz": "BEARISH",
                    "macd_divergence": "NONE",
                },
            ],
        )
        self.assertEqual(snapshot["aggregate"]["descriptive_confluence"], "BULLISH")
        self.assertFalse(snapshot["authority"]["entry_signal_authorized"])

    def test_bounded_decision_requires_complete_probability_vectors(self) -> None:
        probabilities = {}
        for axis, labels in BOUNDED_SCHEMA.items():
            values = {label: 0.0 for label in labels}
            values[labels[0]] = 1.0
            probabilities[axis] = values
        record = build_bounded_decision_record(
            model_name="offline-fixture",
            as_of_ms=1000,
            probabilities=probabilities,
        )
        self.assertEqual(record["axes"]["market_regime"]["selected"], "TREND")
        self.assertFalse(record["semantics"]["calibrated_trading_probability"])
        self.assertFalse(record["authority"]["provider_call_authorized"])

    def test_bounded_decision_rejects_non_unit_probability_sum(self) -> None:
        probabilities = {}
        for axis, labels in BOUNDED_SCHEMA.items():
            probabilities[axis] = {label: 0.0 for label in labels}
            probabilities[axis][labels[0]] = 1.0
        probabilities["direction"]["LONG"] = 0.5
        with self.assertRaises(ValueError):
            build_bounded_decision_record(
                model_name="offline-fixture",
                as_of_ms=1000,
                probabilities=probabilities,
            )

    def test_adapter_preserves_v0_1_score_and_authority(self) -> None:
        adapted = attach_research_sidecars(
            opportunity={"symbol": "BTCUSDT", "score": 72.5, "bias": "LONG"},
            market_event_radar={
                "schema": "qookey-market-event-radar-snapshot-v0.1",
                "symbol": "BTCUSDT",
            },
        )
        self.assertEqual(adapted["original_score"], 72.5)
        self.assertEqual(adapted["opportunity_v0_1"]["score"], 72.5)
        self.assertTrue(adapted["invariants"]["opportunity_score_unchanged"])
        self.assertFalse(adapted["authority"]["candidate_reranking_authorized"])


if __name__ == "__main__":
    unittest.main()
