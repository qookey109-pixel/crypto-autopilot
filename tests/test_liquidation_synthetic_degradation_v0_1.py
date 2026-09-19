from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.liquidation_quality_context_v0_1 import (
    build_liquidation_quality_context,
)
from crypto_autopilot.research.liquidation_synthetic_degradation_v0_1 import (
    LiquidationSyntheticDegradationPolicy,
    degrade_liquidation_snapshot,
    liquidation_synthetic_degradation_policy_from_config,
)
from crypto_autopilot.research.venue_local_liquidation_summary_v0_1 import (
    build_venue_local_liquidation_summary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "liquidation_synthetic_degradation_v0_1.json"


def sample_snapshot():
    return build_liquidation_quality_context(
        symbol="BTCUSDT",
        as_of_ms=10_000,
        input_class="synthetic_fixture",
        evidence=[
            {
                "exchange": "binance",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                "side_semantics": "LONG_LIQUIDATED",
                "event_timestamp_ms": 9000,
                "observed_at_ms": 9001,
                "available_at_ms": 9002,
                "price": 100,
                "quantity": 4,
            },
            {
                "exchange": "bybit",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
                "side_semantics": "LONG_LIQUIDATED",
                "event_timestamp_ms": 9050,
                "observed_at_ms": 9051,
                "available_at_ms": 9052,
                "price": 100,
                "quantity": 9,
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
                "quantity": 2,
            },
            {
                "exchange": "binance",
                "symbol": "BTCUSDT",
                "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                "side_semantics": "LONG_LIQUIDATED",
                "event_timestamp_ms": 9200,
                "observed_at_ms": 9201,
                "available_at_ms": 9202,
                "price": 100,
                "quantity": 1,
            },
        ],
    )


class LiquidationSyntheticDegradationV01Tests(unittest.TestCase):
    def test_drops_explicit_indices_and_is_replayable(self) -> None:
        one = degrade_liquidation_snapshot(
            snapshot=sample_snapshot(),
            venue="binance",
            drop_event_indices=[1],
        )
        two = degrade_liquidation_snapshot(
            snapshot=sample_snapshot(),
            venue="binance",
            drop_event_indices=[1],
        )

        self.assertEqual(one, two)
        self.assertEqual(one["event_count"], 2)
        self.assertEqual(one["venues_present"], ["binance"])
        self.assertEqual(
            one["synthetic_degradation"]["scenario_id"],
            "drop_indices:1",
        )
        self.assertEqual(
            {event["coverage_quality"] for event in one["events"]},
            {"DEGRADED_OR_UNKNOWN"},
        )
        self.assertTrue(
            all(event["exchange"] == "binance" for event in one["events"])
        )
        self.assertIsNone(
            one["synthetic_degradation"]["real_missingness_rate_estimate"]
        )
        self.assertIsNone(one["synthetic_degradation"]["correction_weight"])

    def test_output_can_feed_venue_local_summary(self) -> None:
        degraded = degrade_liquidation_snapshot(
            snapshot=sample_snapshot(),
            venue="binance",
            drop_event_indices=[0, 2],
        )
        summary = build_venue_local_liquidation_summary(
            snapshot=degraded,
            venue="binance",
        )
        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["coverage_quality"], "DEGRADED_OR_UNKNOWN")

    def test_can_drop_all_events_for_zero_observation_stress(self) -> None:
        degraded = degrade_liquidation_snapshot(
            snapshot=sample_snapshot(),
            venue="binance",
            drop_event_indices=[0, 1, 2],
        )
        self.assertEqual(degraded["event_count"], 0)
        self.assertEqual(degraded["events"], [])
        self.assertEqual(degraded["venues_present"], [])

    def test_non_synthetic_input_fails_closed(self) -> None:
        snapshot = sample_snapshot()
        for input_class in (
            "existing_non_holdout_fixture",
            "provider_live",
            "replacement_holdout",
        ):
            with self.subTest(input_class=input_class):
                with self.assertRaises(ValueError):
                    degrade_liquidation_snapshot(
                        snapshot={**snapshot, "input_class": input_class},
                        venue="binance",
                        drop_event_indices=[0],
                    )

    def test_invalid_drop_indices_fail_closed(self) -> None:
        snapshot = sample_snapshot()
        for values in ([], [-1], [True], [0, 0], [3]):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    degrade_liquidation_snapshot(
                        snapshot=snapshot,
                        venue="binance",
                        drop_event_indices=values,
                    )

    def test_unknown_or_empty_venue_fails_closed(self) -> None:
        snapshot = sample_snapshot()
        for venue in ("", "okx"):
            with self.subTest(venue=venue):
                with self.assertRaises(ValueError):
                    degrade_liquidation_snapshot(
                        snapshot=snapshot,
                        venue=venue,
                        drop_event_indices=[0],
                    )

    def test_config_keeps_random_real_and_operational_authority_closed(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            liquidation_synthetic_degradation_policy_from_config(payload),
            LiquidationSyntheticDegradationPolicy(),
        )
        self.assertTrue(payload["policy"]["synthetic_degradation_authorized"])
        self.assertTrue(
            all(
                value is False
                for key, value in payload["policy"].items()
                if key != "synthetic_degradation_authorized"
            )
        )


if __name__ == "__main__":
    unittest.main()
