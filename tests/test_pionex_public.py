import unittest
from unittest.mock import patch

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient


class PionexPublicTests(unittest.TestCase):
    def test_kline_parser_sorts_chronologically(self) -> None:
        client = PionexPublicClient()
        fixture = {
            "result": True,
            "data": {
                "klines": [
                    {"time": 2, "open": "2", "high": "3", "low": "1", "close": "2.5", "volume": "20"},
                    {"time": 1, "open": "1", "high": "2", "low": "0.5", "close": "1.5", "volume": "10"},
                ]
            },
        }
        with patch.object(client, "_get_json", return_value=fixture):
            candles = client.get_klines("BTC_USDT_PERP", "15M", limit=2)
        self.assertEqual([c.time_ms for c in candles], [1, 2])
        self.assertEqual(candles[0].close, 1.5)

    def test_invalid_interval_fails_before_network(self) -> None:
        client = PionexPublicClient()
        with self.assertRaises(ValueError):
            client.get_klines("BTC_USDT_PERP", "17M")


if __name__ == "__main__":
    unittest.main()
