from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.liquidation_cross_venue_gate_v0_1 import (
    CROSS_VENUE_BLOCKED,
    VENUE_LOCAL_ONLY,
    LiquidationCrossVenueGatePolicy,
    assess_liquidation_cross_venue_gate,
    liquidation_cross_venue_gate_policy_from_config,
)
from crypto_autopilot.research.liquidation_quality_context_v0_1 import (
    build_liquidation_quality_context,
)
from crypto_autopilot.research.venue_local_liquidation_summary_v0_1 import (
    build_venue_local_liquidation_summary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "liquidation_cross_venue_gate_v0_1.json"


def snapshots():
    context = build_liquidation_quality_context(
        symbol="BTCUSDT",
        as_of_ms=10_000,
        input_class="synthetic_fixture",
        evidence=[
            {
                "exchange": "bybit",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
                "side_semantics": "LONG_LIQUIDATED",
                "event_timestamp_ms": 9000,
                "observed_at_ms": 9001,
                "available_at_ms": 9002,
                "price": 100,
                "quantity": 2,
            },
            {
                "exchange": "binance",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                "side_semantics": "SHORT_LIQUIDATED",
                "event_timestamp_ms": 9100,
                "observed_at_ms": 9101,
                "available_at_ms": 9102,
                "price": 100,
                "quantity": 3,
            },
        ],
    )
    return {
        venue: build_venue_local_liquidation_summary(
            snapshot=context,
            venue=venue,
        )
        for venue in ("bybit", "binance", "okx")
    }


class LiquidationCrossVenueGateV01Tests(unittest.TestCase):
    def test_single_venue_is_venue_local_only(self) -> None:
        by_venue = snapshots()
        result = assess_liquidation_cross_venue_gate(
            summaries=[by_venue["bybit"]]
        )
        self.assertEqual(result["decision"], VENUE_LOCAL_ONLY)
        self.assertEqual(result["venue_count"], 1)
        self.assertFalse(result["cross_venue_requested"])
        self.assertFalse(result["cross_venue_aggregation_permitted"])

    def test_multiple_venues_are_blocked_without_combining_notionals(self) -> None:
        by_venue = snapshots()
        result = assess_liquidation_cross_venue_gate(
            summaries=[by_venue["bybit"], by_venue["binance"]]
        )
        self.assertEqual(result["decision"], CROSS_VENUE_BLOCKED)
        self.assertEqual(result["venue_count"], 2)
        self.assertTrue(result["cross_venue_requested"])
        self.assertFalse(result["cross_venue_aggregation_permitted"])
        self.assertNotIn("gross_liquidated_notional_usd", result)
        self.assertNotIn("side_imbalance", result)
        self.assertNotIn("venue_weight", result)

    def test_empty_venue_metadata_can_still_be_seen_but_not_combined(self) -> None:
        by_venue = snapshots()
        result = assess_liquidation_cross_venue_gate(
            summaries=[by_venue["bybit"], by_venue["okx"]]
        )
        self.assertEqual(result["decision"], CROSS_VENUE_BLOCKED)
        okx = next(item for item in result["venues"] if item["venue"] == "okx")
        self.assertEqual(okx["event_count"], 0)
        self.assertIsNone(okx["coverage_quality"])

    def test_duplicate_venue_fails_closed(self) -> None:
        by_venue = snapshots()
        with self.assertRaises(ValueError):
            assess_liquidation_cross_venue_gate(
                summaries=[by_venue["bybit"], by_venue["bybit"]]
            )

    def test_misaligned_symbol_time_or_input_class_fails_closed(self) -> None:
        by_venue = snapshots()
        original = by_venue["binance"]
        for changed in (
            {**original, "symbol": "ETHUSDT"},
            {**original, "as_of_ms": 10_001},
            {**original, "input_class": "existing_non_holdout_fixture"},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    assess_liquidation_cross_venue_gate(
                        summaries=[by_venue["bybit"], changed]
                    )

    def test_wrong_schema_and_empty_input_fail_closed(self) -> None:
        by_venue = snapshots()
        with self.assertRaises(ValueError):
            assess_liquidation_cross_venue_gate(summaries=[])
        with self.assertRaises(ValueError):
            assess_liquidation_cross_venue_gate(
                summaries=[
                    {
                        **by_venue["bybit"],
                        "schema": "wrong",
                    }
                ]
            )

    def test_config_has_zero_aggregation_or_operational_authority(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            liquidation_cross_venue_gate_policy_from_config(payload),
            LiquidationCrossVenueGatePolicy(),
        )
        self.assertTrue(payload["policy"]["comparability_gate_authorized"])
        self.assertTrue(
            all(
                value is False
                for key, value in payload["policy"].items()
                if key != "comparability_gate_authorized"
            )
        )


if __name__ == "__main__":
    unittest.main()
