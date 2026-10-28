from __future__ import annotations

import unittest
from dataclasses import replace

from crypto_autopilot.paper.cloud_loop_v0_1 import CompleteTapePionexFeed, CloudLoopReviewRequired
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.validated_tape_client_v0_1 import ValidatedTapeClient
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_cloud_paper_loop_v0_1 import TICK, TapeClient, trade
from unittest.mock import patch


class ValidatedTapeClientTests(unittest.TestCase):
    def feed(self, trades):
        client = TapeClient(trades)
        wrapped = ValidatedTapeClient(client)
        return client, CompleteTapePionexFeed(
            client=wrapped, policy=LivePaperPolicy(), before_request=lambda: None,
        )

    def test_nonfinite_middle_trade_is_not_silently_dropped(self):
        trades = [trade(1, TICK-2000), trade(2, TICK-800),
                  replace(trade(3, TICK-600), price=float("nan")), trade(4, TICK-400)]
        client, feed = self.feed(trades)
        with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
            feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK, since_ms=TICK-1000)
        self.assertEqual(client.calls, ["book", ("trades", 500)])

    def test_invalid_non_best_book_level_or_trade_size_stops(self):
        for value in (float("nan"), float("inf"), -1.0, 0.0):
            with self.subTest(value=value):
                client, feed = self.feed([trade(1, TICK-2000),
                                          replace(trade(2, TICK-500), size=value)])
                with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
                    feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK, since_ms=TICK-1000)
                client, feed = self.feed([trade(1, TICK-2000), trade(2, TICK-500)])
                original = client.get_order_book
                def bad_book(symbol, *, limit):
                    book = original(symbol, limit=limit)
                    return replace(book, bids=book.bids + ((value, 1.0),))
                client.get_order_book = bad_book
                with self.assertRaisesRegex(CloudLoopReviewRequired, "ORDER_BOOK_INVALID"):
                    feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK, since_ms=TICK-1000)
                self.assertEqual(client.calls, ["book"])

    def test_valid_data_preserves_frame_and_provider_calls(self):
        client, feed = self.feed([trade(1, TICK-2000), trade(2, TICK-500)])
        frame = feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK, since_ms=TICK-1000)
        self.assertEqual(frame.source_trade_count, 1)
        self.assertEqual(frame.provider_request_count, 2)
        self.assertEqual(client.calls, ["book", ("trades", 500)])

    def test_prepaid_guarded_runtime_uses_validation(self):
        case = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        case.setUp()
        self.addCleanup(case.doCleanups)
        with patch.object(fixtures, "build_runtime_composition", build_runtime_composition):
            composition = case.runtime()
        self.assertIsInstance(composition.client, ValidatedTapeClient)
        self.assertEqual(case.sdk.calls, [])


if __name__ == "__main__":
    unittest.main()
