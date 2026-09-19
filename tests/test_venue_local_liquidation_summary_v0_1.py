from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.liquidation_quality_context_v0_1 import (
    build_liquidation_quality_context,
)
from crypto_autopilot.research.venue_local_liquidation_summary_v0_1 import (
    VenueLocalLiquidationSummaryPolicy,
    build_venue_local_liquidation_summary,
    venue_local_liquidation_summary_policy_from_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "venue_local_liquidation_summary_v0_1.json"


def sample_snapshot():
    return build_liquidation_quality_context(
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
                "exchange": "bybit",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
                "side_semantics": "SHORT_LIQUIDATED",
                "event_timestamp_ms": 9100,
                "observed_at_ms": 9101,
                "available_at_ms": 9102,
                "price": 100,
                "quantity": 1,
            },
            {
                "exchange": "binance",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                "side_semantics": "SHORT_LIQUIDATED",
                "event_timestamp_ms": 9200,
                "observed_at_ms": 9201,
                "available_at_ms": 9202,
                "price": 100,
                "quantity": 5,
            },
        ],
    )


class VenueLocalLiquidationSummaryV01Tests(unittest.TestCase):
    def test_summarizes_only_requested_venue(self) -> None:
        summary = build_venue_local_liquidation_summary(
            snapshot=sample_snapshot(),
            venue="bybit",
        )
        self.assertEqual(summary["venue"], "bybit")
        self.assertEqual(summary["event_count"], 2)
        self.assertEqual(summary["long_liquidated_notional_usd"], 200.0)
        self.assertEqual(summary["short_liquidated_notional_usd"], 100.0)
        self.assertEqual(summary["gross_liquidated_notional_usd"], 300.0)
        self.assertAlmostEqual(summary["side_imbalance"], 1 / 3)
        self.assertEqual(summary["max_event_notional_usd"], 200.0)
        self.assertEqual(summary["first_event_timestamp_ms"], 9000)
        self.assertEqual(summary["last_event_timestamp_ms"], 9100)
        self.assertFalse(
            summary["authority"]["cross_venue_aggregation_authorized"]
        )
        self.assertFalse(summary["authority"]["signal_generation_authorized"])

    def test_binance_is_not_mixed_into_bybit_summary(self) -> None:
        summary = build_venue_local_liquidation_summary(
            snapshot=sample_snapshot(),
            venue="bybit",
        )
        self.assertEqual(summary["gross_liquidated_notional_usd"], 300.0)

        binance = build_venue_local_liquidation_summary(
            snapshot=sample_snapshot(),
            venue="binance",
        )
        self.assertEqual(binance["gross_liquidated_notional_usd"], 500.0)
        self.assertEqual(
            binance["coverage_quality"],
            "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
        )

    def test_empty_venue_does_not_fabricate_coverage(self) -> None:
        snapshot = build_liquidation_quality_context(
            symbol="BTCUSDT",
            as_of_ms=100,
            input_class="synthetic_fixture",
            evidence=[],
        )
        summary = build_venue_local_liquidation_summary(
            snapshot=snapshot,
            venue="okx",
        )
        self.assertEqual(summary["event_count"], 0)
        self.assertEqual(summary["gross_liquidated_notional_usd"], 0.0)
        self.assertEqual(summary["side_imbalance"], 0.0)
        self.assertIsNone(summary["coverage_quality"])
        self.assertIsNone(summary["first_event_timestamp_ms"])
        self.assertIsNone(summary["last_event_timestamp_ms"])

    def test_mixed_coverage_quality_for_one_venue_fails_closed(self) -> None:
        snapshot = sample_snapshot()
        snapshot["events"].append(
            {
                **snapshot["events"][0],
                "event_timestamp_ms": 9300,
                "observed_at_ms": 9301,
                "available_at_ms": 9302,
                "coverage_quality": "DEGRADED_OR_UNKNOWN",
            }
        )
        with self.assertRaises(ValueError):
            build_venue_local_liquidation_summary(
                snapshot=snapshot,
                venue="bybit",
            )

    def test_wrong_schema_or_unknown_venue_fails_closed(self) -> None:
        snapshot = sample_snapshot()
        with self.assertRaises(ValueError):
            build_venue_local_liquidation_summary(
                snapshot={**snapshot, "schema": "wrong"},
                venue="bybit",
            )
        with self.assertRaises(ValueError):
            build_venue_local_liquidation_summary(
                snapshot=snapshot,
                venue="hyperliquid",
            )

    def test_config_keeps_every_operational_authority_closed(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            venue_local_liquidation_summary_policy_from_config(payload),
            VenueLocalLiquidationSummaryPolicy(),
        )
        self.assertTrue(payload["policy"]["venue_local_summary_authorized"])
        self.assertTrue(
            all(
                value is False
                for key, value in payload["policy"].items()
                if key != "venue_local_summary_authorized"
            )
        )


if __name__ == "__main__":
    unittest.main()
