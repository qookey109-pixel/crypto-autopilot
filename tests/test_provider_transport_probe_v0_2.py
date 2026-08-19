from __future__ import annotations

import json
import unittest

from crypto_autopilot.provider_transport_probe_v0_2 import (
    ProbeError,
    load_probe_authority,
    result_exit_code,
    validate_binance_transport,
    validate_pionex_transport,
)


class ProviderTransportProbeV02Tests(unittest.TestCase):
    def test_frozen_probe_authority_preserves_blocked_boundaries(self) -> None:
        protocol, pionex, binance = load_probe_authority()
        self.assertEqual(protocol["status"], "PROTOCOL_FROZEN_BEFORE_TRANSPORT_EVIDENCE")
        self.assertEqual(len(pionex), 15)
        self.assertEqual(len(binance), 15)
        boundary = protocol["authorization_boundary"]
        self.assertIs(boundary["transport_probe_execution_authorized"], True)
        self.assertIs(boundary["metadata_capture_execution_authorized"], False)
        self.assertIs(boundary["metadata_only_r2_writes_authorized"], False)
        self.assertIs(boundary["holdout_candle_access_authorized"], False)
        self.assertIs(boundary["replacement_holdout_freeze_authorized"], False)
        self.assertIs(boundary["source_switch_authorized"], False)
        self.assertIs(boundary["staged_trade_kline_w1_materialization_authorized"], False)
        self.assertIs(boundary["live_trading_authorized"], False)

    def test_pionex_transport_contract_accepts_selected_symbols_without_emitting_values(self) -> None:
        raw = json.dumps(
            {
                "data": {
                    "symbols": [
                        {"symbol": "BTC_USDT_PERP", "quoteStep": "0.1"},
                        {"symbol": "ETH_USDT_PERP", "quoteStep": "0.01"},
                    ]
                }
            }
        ).encode()
        count = validate_pionex_transport(raw, ("BTC_USDT_PERP", "ETH_USDT_PERP"))
        self.assertEqual(count, 2)

    def test_pionex_transport_contract_fails_on_missing_quote_step(self) -> None:
        raw = json.dumps(
            {"data": {"symbols": [{"symbol": "BTC_USDT_PERP"}]}}
        ).encode()
        with self.assertRaisesRegex(ProbeError, "quoteStep missing"):
            validate_pionex_transport(raw, ("BTC_USDT_PERP",))

    def test_binance_transport_contract_accepts_selected_symbols_without_emitting_values(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
                            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                        ],
                    },
                    {
                        "symbol": "ETHUSDT",
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                        ],
                    },
                ]
            }
        ).encode()
        count = validate_binance_transport(raw, ("BTCUSDT", "ETHUSDT"))
        self.assertEqual(count, 2)

    def test_binance_transport_contract_fails_on_missing_tick_size(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "filters": [{"filterType": "PRICE_FILTER"}],
                    }
                ]
            }
        ).encode()
        with self.assertRaisesRegex(ProbeError, "PRICE_FILTER.tickSize contract missing"):
            validate_binance_transport(raw, ("BTCUSDT",))

    def test_duplicate_selected_symbol_fails_closed(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.1"}],
                    },
                    {
                        "symbol": "BTCUSDT",
                        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.1"}],
                    },
                ]
            }
        ).encode()
        with self.assertRaisesRegex(ProbeError, "duplicate selected symbol"):
            validate_binance_transport(raw, ("BTCUSDT",))

    def test_probe_result_exit_code(self) -> None:
        self.assertEqual(result_exit_code({"status": "PASS"}), 0)
        self.assertEqual(result_exit_code({"status": "BLOCKED"}), 2)
        self.assertEqual(result_exit_code({"status": "FAIL"}), 2)


if __name__ == "__main__":
    unittest.main()
