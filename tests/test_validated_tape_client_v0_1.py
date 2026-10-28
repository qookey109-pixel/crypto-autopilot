from __future__ import annotations

import unittest
from dataclasses import asdict, replace

from crypto_autopilot.paper.cloud_loop_v0_1 import CompleteTapePionexFeed, CloudLoopReviewRequired, run_cloud_step
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition
from crypto_autopilot.features.market import OrderBookSnapshot
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame, LivePaperPolicy
from crypto_autopilot.risk import plan_position_size
from crypto_autopilot.paper.validated_tape_client_v0_1 import ValidatedTapeClient
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_cloud_paper_loop_v0_1 import TICK, TapeClient, trade
from test_cloud_paper_composition_v0_1 import (
    FakeClient, FakeReservationLedger, MemoryStore, composition, make_budget_guard,
)
from unittest.mock import patch

from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient


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

    def test_equal_timestamp_different_prices_stops_before_frame(self):
        client, feed = self.feed([
            trade(1, TICK-2000), trade(2, TICK-500),
            replace(trade(3, TICK-500), price=101.0),
        ])
        with self.assertRaisesRegex(CloudLoopReviewRequired, "ORDER_AMBIGUOUS"):
            feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK, since_ms=TICK-1000)
        self.assertEqual(client.calls, ["book", ("trades", 500)])

    def test_raw_depth_and_trades_are_validated_before_existing_parser(self):
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        guarded = ValidatedTapeClient(client)
        good_depth = {"result": True, "data": {
            "bids": [["100", "2"]], "asks": [["101", "3"]], "updateTime": TICK,
        }}
        with patch.object(client, "_get_json", return_value=good_depth) as request:
            book = guarded.get_order_book("BTC_USDT_PERP", limit=20)
        self.assertEqual(book.bids, ((100.0, 2.0),))
        request.assert_called_once()
        for row in (["102"], "malformed", [True, "1"], ["NaN", "1"]):
            data = {"result": True, "data": {
                "bids": [["100", "2"], row], "asks": [["101", "3"]], "updateTime": TICK,
            }}
            with self.subTest(row=row), patch.object(client, "_get_json", return_value=data) as request:
                with self.assertRaisesRegex(CloudLoopReviewRequired, "ORDER_BOOK_INVALID"):
                    guarded.get_order_book("BTC_USDT_PERP", limit=20)
                request.assert_called_once()
        for value in (True, "", "NaN"):
            data = {"result": True, "data": {"trades": [
                {"price": value, "size": "2", "timestamp": TICK, "tradeId": "1"},
            ]}}
            with self.subTest(value=value), patch.object(client, "_get_json", return_value=data) as request:
                with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
                    guarded.get_recent_trades("BTC_USDT_PERP", limit=500)
                request.assert_called_once()
        good_trades = {"result": True, "data": {"trades": [
            {"price": "100", "size": "2", "timestamp": TICK, "tradeId": "1"},
        ]}}
        with patch.object(client, "_get_json", return_value=good_trades) as request:
            trades = guarded.get_recent_trades("BTC_USDT_PERP", limit=500)
        self.assertEqual(trades[0].price, 100.0)
        request.assert_called_once()

    def test_raw_timestamps_must_be_exact_positive_integers(self):
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        guarded = ValidatedTapeClient(client)
        for timestamp in (True, 0, None, 123.9, "123.9", "", -1, "9" * 5000):
            depth = {"result": True, "data": {
                "bids": [["100", "2"]], "asks": [["101", "3"]], "updateTime": timestamp,
            }}
            trades = {"result": True, "data": {"trades": [
                {"price": "100", "size": "2", "timestamp": timestamp, "tradeId": "1"},
            ]}}
            with self.subTest(timestamp=timestamp), patch.object(client, "_get_json", return_value=depth):
                with self.assertRaisesRegex(CloudLoopReviewRequired, "ORDER_BOOK_INVALID"):
                    guarded.get_order_book("BTC_USDT_PERP", limit=20)
            with self.subTest(timestamp=timestamp), patch.object(client, "_get_json", return_value=trades):
                with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
                    guarded.get_recent_trades("BTC_USDT_PERP", limit=500)
        depth = {"result": True, "timestamp": str(TICK), "data": {
            "bids": [["100", "2"]], "asks": [["101", "3"]],
        }}
        with patch.object(client, "_get_json", return_value=depth):
            self.assertEqual(guarded.get_order_book("BTC_USDT_PERP", limit=20).update_time_ms, TICK)

    def test_active_position_invalid_tape_preserves_account_and_reservation(self):
        symbol = "BTC_USDT_PERP"
        strategy_id = "synthetic-ci-only"
        candidate = {
            "symbol": symbol,
            "strategy_family": "TREND_FOLLOWING",
            "as_of_ms": 419000,
            "family_validation_report": {
                "schema": "qookey-strategy-family-validation-report-v0.1",
                "family": "TREND_FOLLOWING",
                "category": "fixture",
                "state": "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
                "reasons": ["synthetic_ci_fixture"],
                "coverage": {}, "policy": {}, "lineage": {},
                "authority": {
                    "research_evidence_only": True,
                    "family_registry_mutated": False,
                    "strategy_edge_claimed": False,
                    "provider_requests_performed": False,
                    "r2_accessed": False,
                    "holdout_accessed": False,
                    "promotion_authority": 0,
                    "position_sizing_authorized": False,
                    "paper_execution_authorized": False,
                    "trade_plan_authorized": False,
                    "real_money_order_authorized": False,
                    "live_trading_authorized": False,
                },
                "limitations": [],
            },
            "position_sizing_plan": asdict(plan_position_size(
                direction="LONG", equity_usd=10000.0,
                entry_price=100.0, stop_price=99.0,
            )),
        }
        spec = {"strategy_id": strategy_id, "candidate": candidate, "target_price": 105.0}

        class InitialFeed:
            def fetch_frame(self, symbol, *, tick_time_ms, since_ms):
                return LivePaperMarketFrame(
                    provider="FIXTURE_PUBLIC", symbol=symbol, time_ms=tick_time_ms,
                    source_time_ms=tick_time_ms - 1, open=100.0, high=101.0,
                    low=99.5, close=100.5, mark_price=100.5,
                    available_notional_usd=4000.0, provider_request_count=2,
                    source_trade_count=4,
                )

        registry = {
            "schema": "qookey-cloud-paper-strategy-registry-v0.1",
            "status": "SYNTHETIC_TEST_ONLY", "strategies": [{"strategy_id": strategy_id}],
        }
        store = MemoryStore()
        first = run_cloud_step(
            tick_ms=420000, previous_slot=None, store=store,
            feed=InitialFeed(), market_supplier=lambda: {
                "context_status": "REGIME_UNAVAILABLE", "provider_requests_performed": 0,
            }, candidate_supplier=lambda market, state: (spec,),
            strategy_registry=registry, before_external=lambda: None,
        )
        self.assertEqual(first["account"]["open_position_count"], 1)
        before = dict(store.objects)

        class InvalidClient(FakeClient):
            def get_order_book(self, symbol, *, limit):
                self.calls.append("book")
                return OrderBookSnapshot(symbol=symbol, bids=((100.0, 2.0),),
                    asks=((101.0, 3.0),), update_time_ms=1319999)
            def get_recent_trades(self, symbol, *, limit):
                self.calls.append("trades")
                return [trade(1, 420000), trade(2, 1319000),
                        replace(trade(3, 1319500), price=float("nan")),
                        trade(4, 1319900)]

        client = InvalidClient()
        ledger = FakeReservationLedger()
        runtime = composition(
            ValidatedTapeClient(client), store, guard=make_budget_guard(now_ms=1320000),
            reservation_ledger=ledger,
        )
        with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
            runtime.run_slot(tick_ms=1320000, previous_slot=first["slot_id"],
                             activation_enabled=True, run_id="synthetic-open-position")
        self.assertEqual({key: store.objects[key] for key in before}, before)
        self.assertEqual(len(ledger.reservations), 1)
        self.assertEqual(ledger.settlements, [])
        self.assertEqual(runtime.budget_guard.attempted_usage().provider_requests, 2)
        self.assertEqual(client.calls, ["book", "trades"])
        self.assertFalse(any(kind in {"cloud-result", "cloud-report"}
                             for kind, _ in set(store.objects) - set(before)))

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
