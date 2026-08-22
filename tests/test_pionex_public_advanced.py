from __future__ import annotations

import unittest
from unittest.mock import patch

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient


class PionexPublicAdvancedTests(unittest.TestCase):
    def test_public_trades_depth_and_derivative_parsers(self) -> None:
        client = PionexPublicClient()
        trade_fixture = {
            "result": True,
            "data": {
                "trades": [
                    {
                        "symbol": "BTC_USDT_PERP",
                        "tradeId": "2",
                        "price": "101",
                        "size": "0.5",
                        "side": "sell",
                        "timestamp": 2,
                    },
                    {
                        "symbol": "BTC_USDT_PERP",
                        "tradeId": "1",
                        "price": "100",
                        "size": "1",
                        "side": "buy",
                        "timestamp": 1,
                    },
                ]
            },
        }
        with patch.object(client, "_get_json", return_value=trade_fixture) as request:
            trades = client.get_recent_trades("BTC_USDT_PERP", limit=10)
        request.assert_called_once_with(
            "/api/v1/market/trades", {"symbol": "BTC_USDT_PERP", "limit": 10}
        )
        self.assertEqual([item.trade_id for item in trades], ["1", "2"])
        self.assertEqual(trades[0].side, "BUY")

        depth_fixture = {
            "result": True,
            "data": {"bids": [["99", "2"]], "asks": [["101", "3"]], "updateTime": 7},
        }
        with patch.object(client, "_get_json", return_value=depth_fixture):
            book = client.get_order_book("BTC_USDT_PERP", limit=20)
        self.assertEqual(book.bids, ((99.0, 2.0),))
        self.assertEqual(book.update_time_ms, 7)

        funding_fixture = {
            "result": True,
            "data": {
                "rates": [
                    {"fundingTime": 2, "fundingRate": "0.002"},
                    {"fundingTime": 1, "fundingRate": "0.001"},
                ]
            },
        }
        with patch.object(client, "_get_json", return_value=funding_fixture):
            rates = client.get_funding_rates("BTC_USDT_PERP", limit=2, end_time_ms=99)
        self.assertEqual([item.funding_time_ms for item in rates], [1, 2])

    def test_mark_index_and_open_interest_are_public_read_only(self) -> None:
        client = PionexPublicClient()
        kline_fixture = {
            "result": True,
            "data": {
                "klines": [
                    {"time": 1, "open": "100", "high": "102", "low": "99", "close": "101"}
                ]
            },
        }
        with patch.object(client, "_get_json", return_value=kline_fixture) as request:
            candles = client.get_price_klines(
                "BTC_USDT_PERP", "15M", price_type="mark", limit=1
            )
        request.assert_called_once_with(
            "/api/v1/market/markKlines",
            {"symbol": "BTC_USDT_PERP", "interval": "15M", "limit": 1},
        )
        self.assertEqual(candles[0].volume, 0.0)

        oi_fixture = {
            "result": True,
            "data": {"openInterests": [{"symbol": "BTC_USDT_PERP", "openInterest": "12.5"}]},
        }
        with patch.object(client, "_get_json", return_value=oi_fixture):
            self.assertEqual(client.list_open_interests(), {"BTC_USDT_PERP": 12.5})

        method_names = {name.lower() for name in dir(client)}
        for forbidden in ("create_order", "place_order", "cancel_order", "get_balance"):
            self.assertNotIn(forbidden, method_names)
        self.assertFalse(any(name.startswith("get_position") for name in method_names))


if __name__ == "__main__":
    unittest.main()
