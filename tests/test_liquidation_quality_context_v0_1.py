from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.liquidation_quality_context_v0_1 import (
    LiquidationQualityContextPolicy,
    build_liquidation_quality_context,
    liquidation_quality_context_policy_from_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "liquidation_quality_context_v0_1.json"


class LiquidationQualityContextV01Tests(unittest.TestCase):
    def test_normalizes_three_venue_position_side_events(self) -> None:
        snapshot = build_liquidation_quality_context(
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
                    "price": 60_000,
                    "quantity": 0.5,
                    "notional_usd": 30_000,
                },
                {
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                    "side_semantics": "SHORT_LIQUIDATED",
                    "event_timestamp_ms": 9100,
                    "observed_at_ms": 9101,
                    "available_at_ms": 9102,
                    "price": 60_100,
                    "quantity": 0.25,
                },
                {
                    "exchange": "okx",
                    "symbol": "BTCUSDT",
                    "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_UPDATE",
                    "side_semantics": "LONG_LIQUIDATED",
                    "event_timestamp_ms": 9200,
                    "observed_at_ms": 9201,
                    "available_at_ms": 9202,
                    "price": 59_900,
                    "quantity": 0.2,
                },
            ],
        )

        self.assertEqual(snapshot["event_count"], 3)
        self.assertEqual(snapshot["venues_present"], ["binance", "bybit", "okx"])
        self.assertEqual(
            snapshot["interpretation"],
            "DESCRIPTIVE_LIQUIDATION_CONTEXT_ONLY",
        )
        self.assertEqual(snapshot["events"][0]["notional_usd"], 30_000.0)
        self.assertFalse(
            snapshot["authority"]["cross_venue_aggregation_authorized"]
        )
        self.assertFalse(
            snapshot["authority"]["strategy_router_integration_authorized"]
        )

    def test_generic_buy_sell_side_is_rejected(self) -> None:
        for side in ("BUY", "SELL", "Buy", "Sell"):
            with self.subTest(side=side):
                with self.assertRaises(ValueError):
                    build_liquidation_quality_context(
                        symbol="BTCUSDT",
                        as_of_ms=100,
                        input_class="synthetic_fixture",
                        evidence=[
                            {
                                "exchange": "bybit",
                                "symbol": "BTCUSDT",
                                "coverage_quality": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
                                "side_semantics": side,
                                "event_timestamp_ms": 90,
                                "observed_at_ms": 91,
                                "available_at_ms": 92,
                                "price": 1,
                                "quantity": 1,
                            }
                        ],
                    )

    def test_sampled_venues_cannot_be_upgraded_to_bybit_profile(self) -> None:
        for exchange in ("binance", "okx"):
            with self.subTest(exchange=exchange):
                with self.assertRaises(ValueError):
                    build_liquidation_quality_context(
                        symbol="BTCUSDT",
                        as_of_ms=100,
                        input_class="synthetic_fixture",
                        evidence=[
                            {
                                "exchange": exchange,
                                "symbol": "BTCUSDT",
                                "coverage_quality": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
                                "side_semantics": "LONG_LIQUIDATED",
                                "event_timestamp_ms": 90,
                                "observed_at_ms": 91,
                                "available_at_ms": 92,
                                "price": 1,
                                "quantity": 1,
                            }
                        ],
                    )

    def test_coverage_can_be_downgraded_to_unknown(self) -> None:
        snapshot = build_liquidation_quality_context(
            symbol="BTCUSDT",
            as_of_ms=100,
            input_class="synthetic_fixture",
            evidence=[
                {
                    "exchange": "bybit",
                    "symbol": "BTCUSDT",
                    "coverage_quality": "DEGRADED_OR_UNKNOWN",
                    "side_semantics": "LONG_LIQUIDATED",
                    "event_timestamp_ms": 90,
                    "observed_at_ms": 91,
                    "available_at_ms": 92,
                    "price": 1,
                    "quantity": 1,
                }
            ],
        )
        self.assertEqual(
            snapshot["events"][0]["coverage_quality"],
            "DEGRADED_OR_UNKNOWN",
        )

    def test_future_or_inverted_timestamps_fail_closed(self) -> None:
        base = {
            "exchange": "bybit",
            "symbol": "BTCUSDT",
            "coverage_quality": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
            "side_semantics": "LONG_LIQUIDATED",
            "price": 1,
            "quantity": 1,
        }
        invalid_times = (
            (92, 91, 93),
            (90, 92, 91),
            (90, 91, 101),
        )
        for event_ts, observed_ts, available_ts in invalid_times:
            with self.subTest(
                event_ts=event_ts,
                observed_ts=observed_ts,
                available_ts=available_ts,
            ):
                with self.assertRaises(ValueError):
                    build_liquidation_quality_context(
                        symbol="BTCUSDT",
                        as_of_ms=100,
                        input_class="synthetic_fixture",
                        evidence=[
                            {
                                **base,
                                "event_timestamp_ms": event_ts,
                                "observed_at_ms": observed_ts,
                                "available_at_ms": available_ts,
                            }
                        ],
                    )

    def test_holdout_and_live_provider_input_classes_fail_closed(self) -> None:
        for input_class in (
            "frozen_holdout",
            "replacement_holdout",
            "provider_live",
            "unknown",
        ):
            with self.subTest(input_class=input_class):
                with self.assertRaises(ValueError):
                    build_liquidation_quality_context(
                        symbol="BTCUSDT",
                        as_of_ms=100,
                        input_class=input_class,
                        evidence=[],
                    )

    def test_wrong_symbol_duplicate_and_notional_mismatch_fail_closed(self) -> None:
        row = {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
            "side_semantics": "SHORT_LIQUIDATED",
            "event_timestamp_ms": 90,
            "observed_at_ms": 91,
            "available_at_ms": 92,
            "price": 100,
            "quantity": 2,
        }
        with self.assertRaises(ValueError):
            build_liquidation_quality_context(
                symbol="ETHUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row],
            )
        with self.assertRaises(ValueError):
            build_liquidation_quality_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row, row],
            )
        with self.assertRaises(ValueError):
            build_liquidation_quality_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[{**row, "notional_usd": 199}],
            )

    def test_config_is_exact_source_bound_and_zero_operational_authority(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            liquidation_quality_context_policy_from_config(payload),
            LiquidationQualityContextPolicy(),
        )
        self.assertEqual(
            payload["source"]["upstream_commit_sha"],
            "0e1db87a65dc0cc0b890c2257e10e12cd3966cf7",
        )
        self.assertEqual(
            payload["venue_coverage_profiles"]["binance"],
            "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
        )
        self.assertEqual(
            payload["venue_coverage_profiles"]["okx"],
            "UPSTREAM_DECLARED_THROTTLED_UPDATE",
        )
        self.assertTrue(
            all(
                value is False
                for key, value in payload["policy"].items()
                if key != "prefetched_evidence_ingestion_authorized"
            )
        )


if __name__ == "__main__":
    unittest.main()
