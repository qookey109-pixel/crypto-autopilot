from __future__ import annotations

import json
import unittest
from dataclasses import asdict, replace
from unittest.mock import Mock, patch

from crypto_autopilot.features.market import OrderBookSnapshot, PublicTrade
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, CloudLoopReviewRequired, run_cloud_step
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame
from crypto_autopilot.paper.validated_tape_client_v0_1 import ValidatedTapeClient
from crypto_autopilot.risk import plan_position_size
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_cloud_paper_composition_v0_1 import FakeClient


class PrepaidOpenPositionTapeTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_invalid_tape_retains_real_synthetic_prepaid_reservation(self):
        symbol = "BTC_USDT_PERP"
        strategy_id = "synthetic-ci-only"
        candidate = {
            "symbol": symbol,
            "strategy_family": "TREND_FOLLOWING",
            "as_of_ms": self.f.now - 1000,
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

        with patch.object(fixtures, "build_runtime_composition", build_runtime_composition):
            seed_runtime = self.f.runtime()
        registry = {"schema": "qookey-cloud-paper-strategy-registry-v0.1",
                    "status": "SYNTHETIC_TEST_ONLY",
                    "strategies": [{"strategy_id": strategy_id}]}
        first = run_cloud_step(
            tick_ms=self.f.now, previous_slot=None, store=seed_runtime.store,
            feed=InitialFeed(), market_supplier=lambda: {
                "context_status": "REGIME_UNAVAILABLE", "provider_requests_performed": 0,
            }, candidate_supplier=lambda market, state: (spec,),
            strategy_registry=registry, before_external=seed_runtime.before_external,
        )
        self.assertEqual(first["account"]["open_position_count"], 1)
        before = dict(self.f.sdk.objects)
        first_tick = self.f.now
        self.f.now += SLOT_MS
        self.f._set_run(102)
        self.f.meter = self.f.claim(102)
        db = self.f.sqlite()
        statements = []
        def send(request, timeout):
            payload = json.loads(request.data)
            statements.append(payload["sql"])
            cursor = db.execute(payload["sql"], tuple(payload["params"]))
            names = tuple(row[0] for row in cursor.description or ())
            rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
            db.commit()
            return fixtures.Response(fixtures.body(rows=rows, reads=1, writes=7, size=1088))
        opener = Mock()
        opener.open.side_effect = send

        class InvalidClient(FakeClient):
            def get_order_book(inner, symbol, *, limit):
                inner.calls.append("book")
                return OrderBookSnapshot(symbol=symbol, bids=((100.0, 2.0),),
                    asks=((101.0, 3.0),), update_time_ms=self.f.now - 1)
            def get_recent_trades(inner, symbol, *, limit):
                inner.calls.append("trades")
                def row(ident, time_ms, price):
                    return PublicTrade(symbol=symbol, trade_id=str(ident), price=price,
                                       size=1.0, side="BUY", time_ms=time_ms)
                return [row(1, first_tick, 100.0), row(2, self.f.now-900, 100.0),
                        row(3, self.f.now-600, float("nan")), row(4, self.f.now-100, 100.0)]

        client = InvalidClient()
        with patch.object(fixtures, "build_runtime_composition", build_runtime_composition):
            runtime = self.f.runtime()
        runtime = replace(runtime, client=ValidatedTapeClient(client))
        self.f.sdk.calls.clear()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
                runtime.run_slot(tick_ms=self.f.now, previous_slot=first["slot_id"],
                                 activation_enabled=True, run_id="synthetic-open-position")
        self.assertEqual({key: self.f.sdk.objects[key] for key in before}, before)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloud_paper_budget_reservations WHERE state='RESERVED'").fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloud_paper_budget_reservations WHERE state='SETTLED'").fetchone()[0], 0)
        self.assertEqual(len(statements), 2)
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 3)
        self.assertEqual(runtime.budget_guard.attempted_usage().provider_requests, 2)
        self.assertEqual(client.calls, ["book", "trades"])
        added = set(self.f.sdk.objects) - set(before)
        self.assertFalse(any("/cloud-result/" in key or "/cloud-report/" in key for key in added))


if __name__ == "__main__":
    unittest.main()
