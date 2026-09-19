from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.external_market_context_v0_1 import (
    ExternalMarketContextPolicy,
    build_external_market_context_snapshot,
    external_market_context_policy_from_config,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "external_market_context_sources_v0_1.json"


class ExternalMarketContextV01Tests(unittest.TestCase):
    def test_normalizes_all_six_prefetched_sources(self) -> None:
        snapshot = build_external_market_context_snapshot(
            symbol="BTCUSDT",
            as_of_ms=10_000,
            evidence=[
                {
                    "source_id": "crypto_orderbook_mcp",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9000,
                    "available_at_ms": 9001,
                    "payload": {
                        "exchange": "binance",
                        "bid_depth": 120.0,
                        "ask_depth": 80.0,
                        "imbalance": 0.2,
                        "mid_price": 60000.0,
                    },
                },
                {
                    "source_id": "crypto_liquidations_mcp",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9100,
                    "available_at_ms": 9101,
                    "payload": {
                        "events": [
                            {"side": "BUY", "price": 60000.0, "quantity": 1.0},
                            {"side": "SELL", "price": 60000.0, "quantity": 0.5},
                        ]
                    },
                },
                {
                    "source_id": "pulse_verity",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9200,
                    "available_at_ms": 9201,
                    "payload": {
                        "price": 60005.0,
                        "grade": "consensus",
                        "signature_verified": True,
                        "print_timestamp_ms": 9200,
                    },
                },
                {
                    "source_id": "crypto_rss_mcp",
                    "symbol": None,
                    "observed_at_ms": 9300,
                    "available_at_ms": 9301,
                    "payload": {
                        "entries": [
                            {"title": "BTC market update", "published_ms": 9250}
                        ]
                    },
                },
                {
                    "source_id": "crypto_sentiment_mcp",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9400,
                    "available_at_ms": 9401,
                    "payload": {
                        "sentiment_balance": 0.12,
                        "social_volume": 1500,
                        "social_dominance": 18.5,
                        "trending_words": ["bitcoin", "etf"],
                    },
                },
                {
                    "source_id": "crypto_trending_mcp",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 9500,
                    "available_at_ms": 9501,
                    "payload": {
                        "rank": 1,
                        "price": 60000.0,
                        "change_24h_pct": 2.5,
                        "volume_24h": 2_000_000_000.0,
                        "market_cap": 1_200_000_000_000.0,
                    },
                },
            ],
        )

        self.assertEqual(snapshot["symbol"], "BTCUSDT")
        self.assertEqual(len(snapshot["sources_present"]), 6)
        liquidations = snapshot["sources"]["crypto_liquidations_mcp"]["data"]
        self.assertEqual(liquidations["event_count"], 2)
        self.assertEqual(liquidations["gross_notional"], 90000.0)
        self.assertAlmostEqual(liquidations["side_imbalance"], 1 / 3)
        self.assertTrue(
            snapshot["sources"]["pulse_verity"]["data"]["signature_verified"]
        )
        self.assertFalse(snapshot["authority"]["network_capture_authorized"])
        self.assertFalse(
            snapshot["authority"]["automatic_strategy_selection_authorized"]
        )
        self.assertFalse(
            snapshot["authority"]["external_text_instruction_authority"]
        )

    def test_future_evidence_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_external_market_context_snapshot(
                symbol="BTCUSDT",
                as_of_ms=100,
                evidence=[
                    {
                        "source_id": "crypto_orderbook_mcp",
                        "symbol": "BTCUSDT",
                        "observed_at_ms": 100,
                        "available_at_ms": 101,
                        "payload": {
                            "exchange": "binance",
                            "bid_depth": 1,
                            "ask_depth": 1,
                            "imbalance": 0,
                            "mid_price": 1,
                        },
                    }
                ],
            )

    def test_duplicate_source_fails_closed(self) -> None:
        row = {
            "source_id": "crypto_trending_mcp",
            "symbol": "BTCUSDT",
            "observed_at_ms": 1,
            "available_at_ms": 1,
            "payload": {"rank": 1},
        }
        with self.assertRaises(ValueError):
            build_external_market_context_snapshot(
                symbol="BTCUSDT",
                as_of_ms=10,
                evidence=[row, row],
            )

    def test_wrong_symbol_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_external_market_context_snapshot(
                symbol="BTCUSDT",
                as_of_ms=10,
                evidence=[
                    {
                        "source_id": "crypto_sentiment_mcp",
                        "symbol": "ETHUSDT",
                        "observed_at_ms": 1,
                        "available_at_ms": 2,
                        "payload": {"sentiment_balance": 1.0},
                    }
                ],
            )

    def test_future_pulse_print_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_external_market_context_snapshot(
                symbol="BTCUSDT",
                as_of_ms=10,
                evidence=[
                    {
                        "source_id": "pulse_verity",
                        "symbol": "BTCUSDT",
                        "observed_at_ms": 1,
                        "available_at_ms": 2,
                        "payload": {
                            "price": 100.0,
                            "grade": "consensus",
                            "signature_verified": True,
                            "print_timestamp_ms": 11,
                        },
                    }
                ],
            )

    def test_external_text_control_character_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_external_market_context_snapshot(
                symbol="BTCUSDT",
                as_of_ms=10,
                evidence=[
                    {
                        "source_id": "crypto_rss_mcp",
                        "symbol": None,
                        "observed_at_ms": 1,
                        "available_at_ms": 2,
                        "payload": {
                            "entries": [
                                {
                                    "title": "bad\ncontrol",
                                    "published_ms": 1,
                                }
                            ]
                        },
                    }
                ],
            )

    def test_unsigned_pulse_is_preserved_not_upgraded(self) -> None:
        snapshot = build_external_market_context_snapshot(
            symbol="BTCUSDT",
            as_of_ms=10,
            evidence=[
                {
                    "source_id": "pulse_verity",
                    "symbol": "BTCUSDT",
                    "observed_at_ms": 1,
                    "available_at_ms": 2,
                    "payload": {
                        "price": 100.0,
                        "grade": "indicative",
                        "signature_verified": False,
                        "print_timestamp_ms": 1,
                    },
                }
            ],
        )
        pulse = snapshot["sources"]["pulse_verity"]["data"]
        self.assertFalse(pulse["signature_verified"])
        self.assertEqual(pulse["grade"], "indicative")

    def test_config_pins_six_sources_and_remains_no_io(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            external_market_context_policy_from_config(payload),
            ExternalMarketContextPolicy(),
        )
        self.assertEqual(len(payload["sources"]), 6)
        self.assertTrue(
            all(len(row["upstream_commit_sha"]) == 40 for row in payload["sources"])
        )
        self.assertTrue(
            all(row["license"] == "MIT" for row in payload["sources"])
        )
        self.assertTrue(
            all(
                row["network_capture_authorized"] is False
                for row in payload["sources"]
            )
        )


if __name__ == "__main__":
    unittest.main()
