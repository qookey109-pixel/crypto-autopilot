from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.prefetched_derivatives_context_v0_1 import (
    PrefetchedDerivativesContextPolicy,
    build_prefetched_derivatives_context,
    prefetched_derivatives_context_policy_from_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "prefetched_derivatives_context_v0_1.json"


class PrefetchedDerivativesContextV01Tests(unittest.TestCase):
    def test_normalizes_multi_exchange_derivatives_context(self) -> None:
        snapshot = build_prefetched_derivatives_context(
            symbol="BTCUSDT",
            as_of_ms=10_000,
            input_class="synthetic_fixture",
            evidence=[
                {
                    "kind": "funding",
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9000,
                    "available_at_ms": 9001,
                    "payload": {
                        "funding_rate": 0.0001,
                        "funding_interval_hours": 8,
                    },
                },
                {
                    "kind": "funding",
                    "exchange": "hyperliquid",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9002,
                    "available_at_ms": 9003,
                    "payload": {
                        "funding_rate": -0.00001,
                        "funding_interval_hours": 1,
                    },
                },
                {
                    "kind": "open_interest",
                    "exchange": "bybit",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9100,
                    "available_at_ms": 9101,
                    "payload": {
                        "open_interest_amount": 1000.0,
                        "open_interest_value": 60_000_000.0,
                    },
                },
                {
                    "kind": "long_short_ratio",
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9200,
                    "available_at_ms": 9201,
                    "payload": {
                        "period": "5m",
                        "long_short_ratio": 1.5,
                        "long_pct": 0.6,
                        "short_pct": 0.4,
                    },
                },
            ],
        )

        self.assertEqual(snapshot["symbol"], "BTCUSDT")
        self.assertEqual(
            snapshot["metrics_present"],
            ["funding", "long_short_ratio", "open_interest"],
        )
        self.assertEqual(len(snapshot["metrics"]["funding"]), 2)
        self.assertEqual(
            snapshot["metrics"]["long_short_ratio"][0]["exchange"],
            "binance",
        )
        self.assertEqual(
            snapshot["interpretation"],
            "DESCRIPTIVE_RESEARCH_CONTEXT_ONLY",
        )
        self.assertFalse(snapshot["authority"]["network_capture_authorized"])
        self.assertFalse(
            snapshot["authority"]["strategy_router_integration_authorized"]
        )
        self.assertFalse(snapshot["authority"]["real_money_order_authorized"])

    def test_future_or_inverted_timestamps_fail_closed(self) -> None:
        base = {
            "kind": "funding",
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "payload": {
                "funding_rate": 0.0,
                "funding_interval_hours": 8,
            },
        }
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[{**base, "observed_at_ms": 90, "available_at_ms": 101}],
            )
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[{**base, "observed_at_ms": 91, "available_at_ms": 90}],
            )

    def test_holdout_or_unknown_input_class_fails_closed(self) -> None:
        for input_class in (
            "replacement_holdout",
            "frozen_holdout",
            "provider_live",
            "unknown",
        ):
            with self.subTest(input_class=input_class):
                with self.assertRaises(ValueError):
                    build_prefetched_derivatives_context(
                        symbol="BTCUSDT",
                        as_of_ms=100,
                        input_class=input_class,
                        evidence=[],
                    )

    def test_wrong_symbol_and_duplicate_metric_fail_closed(self) -> None:
        row = {
            "kind": "open_interest",
            "exchange": "okx",
            "symbol": "BTCUSDT",
            "observed_at_ms": 90,
            "available_at_ms": 91,
            "payload": {"open_interest_value": 100.0},
        }
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="ETHUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row],
            )
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row, row],
            )

    def test_long_short_is_binance_only_and_internally_consistent(self) -> None:
        def row(exchange: str, ratio: float, long_share: float, short_share: float):
            return {
                "kind": "long_short_ratio",
                "exchange": exchange,
                "symbol": "BTCUSDT",
                "observed_at_ms": 90,
                "available_at_ms": 91,
                "payload": {
                    "period": "5m",
                    "long_short_ratio": ratio,
                    "long_pct": long_share,
                    "short_pct": short_share,
                },
            }

        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row("bybit", 1.0, 0.5, 0.5)],
            )
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row("binance", 2.0, 0.5, 0.5)],
            )
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[row("binance", 1.5, 0.7, 0.4)],
            )

    def test_open_interest_and_funding_validation_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[
                    {
                        "kind": "open_interest",
                        "exchange": "okx",
                        "symbol": "BTCUSDT",
                        "observed_at_ms": 90,
                        "available_at_ms": 91,
                        "payload": {},
                    }
                ],
            )
        with self.assertRaises(ValueError):
            build_prefetched_derivatives_context(
                symbol="BTCUSDT",
                as_of_ms=100,
                input_class="synthetic_fixture",
                evidence=[
                    {
                        "kind": "funding",
                        "exchange": "binance",
                        "symbol": "BTCUSDT",
                        "observed_at_ms": 90,
                        "available_at_ms": 91,
                        "payload": {
                            "funding_rate": 0.0001,
                            "funding_interval_hours": 25,
                        },
                    }
                ],
            )

    def test_config_is_exact_source_bound_and_no_io(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            prefetched_derivatives_context_policy_from_config(payload),
            PrefetchedDerivativesContextPolicy(),
        )
        self.assertEqual(
            payload["source"]["upstream_commit_sha"],
            "7720d7116e26e578037c519d6fdae0d9ba0e8a75",
        )
        self.assertEqual(
            set(payload["allowed_input_classes"]),
            {"synthetic_fixture", "existing_non_holdout_fixture"},
        )
        self.assertTrue(all(value is False for key, value in payload["policy"].items() if key != "prefetched_evidence_ingestion_authorized"))


if __name__ == "__main__":
    unittest.main()
