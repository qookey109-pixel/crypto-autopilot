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

    def test_ticker_and_book_parsers(self) -> None:
        client = PionexPublicClient()
        ticker_fixture = {
            "result": True,
            "data": {"tickers": [{"symbol": "BTC_USDT_PERP", "close": "60000", "volume": "2", "amount": "120000", "count": 9}]},
        }
        book_fixture = {
            "result": True,
            "data": {"tickers": [{"symbol": "BTC_USDT_PERP", "bidPrice": "59999", "bidSize": "1", "askPrice": "60001", "askSize": "2", "timestamp": 123}]},
        }
        with patch.object(client, "_get_json", return_value=ticker_fixture) as ticker_get:
            ticker = client.list_perpetual_tickers()[0]
        ticker_get.assert_called_once_with("/api/v1/market/tickers", {"type": "PERP"})

        with patch.object(client, "_get_json", return_value=book_fixture) as book_get:
            book = client.list_perpetual_book_tickers()[0]
        book_get.assert_called_once_with("/api/v1/market/bookTickers", {"type": "PERP"})
        self.assertEqual(ticker.quote_amount, 120000.0)
        self.assertEqual(book.ask_price, 60001.0)


if __name__ == "__main__":
    unittest.main()
