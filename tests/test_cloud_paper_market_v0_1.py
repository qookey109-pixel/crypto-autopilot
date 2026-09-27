import unittest
from datetime import UTC, datetime

from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.paper.cloud_market_v0_1 import (
    EARLIEST_CANDLE_MS, HOUR_MS, MarketInputRejected, analyze_capture,
    capture_market, validate_window, validated_candles,
)

NOW = int(datetime(2026, 9, 27, 8, 7, tzinfo=UTC).timestamp() * 1000)


def bars(now=NOW):
    end = now // HOUR_MS * HOUR_MS
    return [Candle(time_ms=end - (240 - i) * HOUR_MS,
                   open=100 + i, high=102 + i, low=99 + i,
                   close=101 + i, volume=1000) for i in range(240)]


class Client:
    def __init__(self):
        self.calls = []

    def list_perpetual_symbols(self):
        self.calls.append("symbols")
        return ["BTC_USDT_PERP", "UNKNOWNX_USDT_PERP"]

    def list_perpetual_tickers(self):
        self.calls.append("tickers")
        return [MarketTicker(symbol=s, close=340, base_volume=1000,
                             quote_amount=1000000, trade_count=100)
                for s in ["BTC_USDT_PERP", "UNKNOWNX_USDT_PERP"]]

    def list_perpetual_book_tickers(self):
        self.calls.append("books")
        return [BookTicker(symbol=s, bid_price=340, bid_size=10,
                           ask_price=340.1, ask_size=10, timestamp_ms=NOW)
                for s in ["BTC_USDT_PERP", "UNKNOWNX_USDT_PERP"]]

    def get_klines(self, symbol, interval, *, limit, end_time_ms):
        self.calls.append(symbol)
        return bars()


class CloudMarketTests(unittest.TestCase):
    def test_exact_post_holdout_boundary(self):
        self.assertEqual(EARLIEST_CANDLE_MS,
                         int(datetime(2026, 9, 4, tzinfo=UTC).timestamp() * 1000))

    def test_holdout_guard_precedes_any_request(self):
        client = Client()
        with self.assertRaisesRegex(MarketInputRejected, "HOLDOUT"):
            capture_market(client, as_of_ms=EARLIEST_CANDLE_MS,
                           allowed_base_assets=frozenset({"BTC"}),
                           before_request=lambda: None)
        self.assertEqual(client.calls, [])

    def test_capture_excludes_unknown_and_preserves_missing_context(self):
        client = Client()
        permits = []
        capture = capture_market(client, as_of_ms=NOW,
                                 allowed_base_assets=frozenset({"BTC"}),
                                 before_request=lambda: permits.append(True))
        self.assertEqual(capture.symbols, ("BTC_USDT_PERP",))
        self.assertEqual(len(permits), 4)
        report = analyze_capture(capture, allowed_base_assets=frozenset({"BTC"}))
        self.assertEqual(report["context_status"], "REGIME_UNAVAILABLE")
        self.assertEqual(report["candidate_specs"], [])
        self.assertFalse(report["execution_selection_performed"])
        self.assertEqual(report["market_evidence"]["BTC_USDT_PERP"]["bar_count"], 240)

    def test_budget_rejection_precedes_provider(self):
        client = Client()
        def deny():
            raise RuntimeError("budget")
        with self.assertRaisesRegex(RuntimeError, "budget"):
            capture_market(client, as_of_ms=NOW,
                           allowed_base_assets=frozenset({"BTC"}), before_request=deny)
        self.assertEqual(client.calls, [])

    def test_missing_duplicate_unclosed_and_stale_bars_rejected(self):
        source = bars()
        for bad in (source[:10], source[:-1], source[:100] + source[101:],
                    source[:100] + source[99:]):
            with self.subTest(length=len(bad)):
                with self.assertRaises(MarketInputRejected):
                    validated_candles(bad, as_of_ms=NOW)
        with self.assertRaises(MarketInputRejected):
            validate_window(True)
