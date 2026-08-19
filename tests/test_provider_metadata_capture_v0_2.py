from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from crypto_autopilot.provider_metadata_capture_suspension_v0_2 import (
    load_transport_blocker,
    suspended_execution_result,
)
from crypto_autopilot.provider_metadata_capture_v0_2 import (
    capture_slot,
    load_and_validate_authority,
    parse_binance_exchange_info,
    parse_pionex_symbols,
)


class ProviderMetadataCaptureV02Tests(unittest.TestCase):
    def test_frozen_historical_capture_protocol_still_parses_for_lineage(self) -> None:
        protocol, pionex, binance = load_and_validate_authority()
        self.assertEqual(len(pionex), 15)
        self.assertEqual(len(binance), 15)
        self.assertEqual(protocol["metadata_capture_window"]["hourly_slot_count"], 194)
        self.assertIs(protocol["authorization_boundary"]["holdout_candle_access_authorized"], False)
        self.assertIs(protocol["authorization_boundary"]["live_trading_authorized"], False)

    def test_latest_transport_blocker_revokes_capture_execution(self) -> None:
        blocker = load_transport_blocker()
        self.assertEqual(blocker["status"], "PASS")
        self.assertEqual(
            blocker["stage"],
            "PROVIDER_EQUIVALENCE_V0_2_METADATA_TRANSPORT_BLOCKED_CAPTURE_SUSPENDED",
        )
        boundary = blocker["authorization_boundary"]
        self.assertIs(boundary["metadata_capture_execution_authorized"], False)
        self.assertIs(boundary["metadata_only_r2_writes_authorized"], False)
        self.assertIs(boundary["holdout_candle_access_authorized"], False)
        self.assertIs(boundary["source_switch_authorized"], False)
        self.assertIs(boundary["live_trading_authorized"], False)

    def test_capture_cli_guard_returns_zero_request_zero_write_suspension(self) -> None:
        for mode in ("connectivity-preflight", "capture"):
            result = suspended_execution_result(requested_mode=mode)
            self.assertEqual(result["status"], "SKIP")
            self.assertEqual(
                result["stage"],
                "PROVIDER_EQUIVALENCE_V0_2_METADATA_TRANSPORT_BLOCKED_CAPTURE_SUSPENDED",
            )
            self.assertEqual(result["requested_mode"], mode)
            self.assertEqual(result["provider_requests_performed"], 0)
            self.assertIs(result["increment_values_emitted"], False)
            self.assertIs(result["r2_client_constructed"], False)
            self.assertIs(result["r2_writes_performed"], False)
            self.assertIs(result["r2_deletes_performed"], False)
            self.assertIs(result["holdout_candles_accessed"], False)
            self.assertIs(result["holdout_evaluated"], False)
            self.assertIs(result["source_switch_authorized"], False)
            self.assertIs(result["w1_materialization_authorized"], False)
            self.assertIs(result["live_trading_authorized"], False)

    def test_parse_pionex_requires_exact_expected_symbols_and_positive_steps(self) -> None:
        raw = json.dumps(
            {
                "data": {
                    "symbols": [
                        {
                            "symbol": "BTC_USDT_PERP",
                            "quoteStep": "0.1",
                            "status": "TRADING",
                            "contractType": "PERP",
                        },
                        {
                            "symbol": "ETH_USDT_PERP",
                            "quoteStep": "0.01",
                            "status": "TRADING",
                            "contractType": "PERP",
                        },
                    ]
                }
            }
        ).encode()
        rows = parse_pionex_symbols(raw, ("BTC_USDT_PERP", "ETH_USDT_PERP"))
        self.assertEqual([row["symbol"] for row in rows], ["BTC_USDT_PERP", "ETH_USDT_PERP"])
        self.assertEqual(rows[0]["price_increment"], "0.1")
        self.assertEqual(rows[1]["price_increment"], "0.01")
        self.assertTrue(all(row["source_field"] == "data.symbols[].quoteStep" for row in rows))

    def test_parse_pionex_missing_symbol_fails_closed(self) -> None:
        raw = json.dumps(
            {
                "data": {
                    "symbols": [
                        {
                            "symbol": "BTC_USDT_PERP",
                            "quoteStep": "0.1",
                            "status": "TRADING",
                            "contractType": "PERP",
                        }
                    ]
                }
            }
        ).encode()
        with self.assertRaisesRegex(RuntimeError, "missing frozen symbols"):
            parse_pionex_symbols(raw, ("BTC_USDT_PERP", "ETH_USDT_PERP"))

    def test_parse_binance_requires_price_filter(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "TRADING",
                        "contractType": "PERPETUAL",
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
                            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                        ],
                    }
                ]
            }
        ).encode()
        rows = parse_binance_exchange_info(raw, ("BTCUSDT",))
        self.assertEqual(rows[0]["price_increment"], "0.10")
        self.assertEqual(
            rows[0]["source_field"],
            "symbols[].filters[filterType=PRICE_FILTER].tickSize",
        )

    def test_nonpositive_increment_fails_closed(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "TRADING",
                        "contractType": "PERPETUAL",
                        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0"}],
                    }
                ]
            }
        ).encode()
        with self.assertRaisesRegex(RuntimeError, "finite and positive"):
            parse_binance_exchange_info(raw, ("BTCUSDT",))

    def test_historical_capture_slot_math_remains_reproducible_but_not_authorized(self) -> None:
        protocol, _, _ = load_and_validate_authority()
        inside = datetime(2026, 8, 21, 3, 47, 12, tzinfo=timezone.utc)
        self.assertEqual(
            capture_slot(inside, protocol),
            datetime(2026, 8, 21, 3, 0, 0, tzinfo=timezone.utc),
        )
        before = datetime(2026, 8, 19, 23, 59, 59, tzinfo=timezone.utc)
        after = datetime(2026, 8, 28, 2, 0, 0, tzinfo=timezone.utc)
        self.assertIsNone(capture_slot(before, protocol))
        self.assertIsNone(capture_slot(after, protocol))


if __name__ == "__main__":
    unittest.main()
