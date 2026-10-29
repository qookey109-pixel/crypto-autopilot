"""Offline synthetic active-position tests for the prepared V0.5 Paper runtime."""
import json
import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, CloudLoopReviewRequired, run_cloud_step
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition as build_seed_runtime
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame
from crypto_autopilot.risk import plan_position_size
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_paper_v05_prepaid_runtime_v0_1 import PaperV05RuntimeTests


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
        self.headers = {}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def getcode(self):
        return 200
    def read(self, limit):
        return self.payload[:limit]


class PaperV05PositionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.outer = PaperV05RuntimeTests("test_default_disabled_has_no_requests")
        self.outer.setUp()
        self.addCleanup(self.outer.doCleanups)
        self.f = self.outer.f
        self.provider_patch = patch("crypto_autopilot.paper.cloud_pionex_client_v0_1.build_opener")
        self.provider = self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)
        pace = patch("crypto_autopilot.paper.cloud_pionex_client_v0_1.CloudPaperPionexPublicClient._pace")
        pace.start()
        self.addCleanup(pace.stop)

    def seed_position(self):
        candidate = {
            "symbol": "BTC_USDT_PERP", "strategy_family": "TREND_FOLLOWING",
            "as_of_ms": self.f.now - 1000,
            "family_validation_report": {
                "schema": "qookey-strategy-family-validation-report-v0.1",
                "family": "TREND_FOLLOWING", "category": "fixture",
                "state": "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
                "reasons": ["synthetic_ci_fixture"], "coverage": {}, "policy": {}, "lineage": {},
                "authority": {
                    "research_evidence_only": True, "family_registry_mutated": False,
                    "strategy_edge_claimed": False, "provider_requests_performed": False,
                    "r2_accessed": False, "holdout_accessed": False, "promotion_authority": 0,
                    "position_sizing_authorized": False, "paper_execution_authorized": False,
                    "trade_plan_authorized": False, "real_money_order_authorized": False,
                    "live_trading_authorized": False,
                },
                "limitations": [],
            },
            "position_sizing_plan": asdict(plan_position_size(
                direction="LONG", equity_usd=10000.0, entry_price=100.0, stop_price=99.0,
            )),
        }
        spec = {"strategy_id": "synthetic-ci-only", "candidate": candidate, "target_price": 105.0}
        registry = {"schema": "qookey-cloud-paper-strategy-registry-v0.1",
                    "status": "SYNTHETIC_TEST_ONLY", "strategies": [{"strategy_id": "synthetic-ci-only"}]}
        class InitialFeed:
            def fetch_frame(inner, symbol, *, tick_time_ms, since_ms):
                return LivePaperMarketFrame(
                    provider="FIXTURE_PUBLIC", symbol=symbol, time_ms=tick_time_ms,
                    source_time_ms=tick_time_ms - 1, open=100.0, high=101.0,
                    low=99.5, close=100.5, mark_price=100.5, available_notional_usd=4000.0,
                    provider_request_count=2, source_trade_count=4,
                )
        with patch.object(fixtures, "build_runtime_composition", build_seed_runtime):
            seed = self.f.runtime()
        report = run_cloud_step(
            tick_ms=self.f.now, previous_slot=None, store=seed.store, feed=InitialFeed(),
            market_supplier=lambda: {"context_status": "REGIME_UNAVAILABLE", "provider_requests_performed": 0},
            candidate_supplier=lambda market, state: (spec,), strategy_registry=registry,
            before_external=seed.before_external,
        )
        self.assertEqual(report["account"]["open_position_count"], 1)
        return report

    def advance(self, *, invalid):
        first = self.seed_position()
        before = dict(self.f.sdk.objects)
        start = self.f.now
        self.f.now += SLOT_MS
        self.f._set_run(102)
        self.f.meter = self.f.claim(102)
        db, _, statements, opener = self.outer.outer.transport()
        def send_provider(request, timeout):
            if "/market/depth" in request.full_url:
                data = {"bids": [["106", "100"]], "asks": [["107", "100"]],
                        "updateTime": self.f.now - 1}
            else:
                data = {"trades": [
                    {"tradeId": "1", "price": "100", "size": "1", "side": "BUY", "timestamp": start},
                    {"tradeId": "2", "price": "NaN" if invalid else "106", "size": "1", "side": "BUY",
                     "timestamp": self.f.now - 100},
                ]}
            return FakeResponse({"result": True, "data": data})
        self.provider.return_value.open.side_effect = send_provider
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            runtime = self.outer.runtime()
            runtime.budget_guard.snapshot = replace(
                runtime.budget_guard.snapshot, pending_storage_bytes=2_097_152,
                pending_new_bytes_day=2_097_152, pending_provider_requests_day=18,
                pending_class_a_day=128, pending_class_b_day=128, pending_class_a_month=128,
                pending_class_b_month=128, pending_class_a_31_days=128, pending_class_b_31_days=128,
            )
            if invalid:
                with self.assertRaisesRegex(CloudLoopReviewRequired, "TRADE_TAPE_INVALID"):
                    runtime.run_slot(tick_ms=self.f.now, previous_slot=first["slot_id"],
                                     activation_enabled=True, run_id="synthetic-open-position")
                result = None
            else:
                result = runtime.run_slot(tick_ms=self.f.now, previous_slot=first["slot_id"],
                                          activation_enabled=True, run_id="synthetic-open-position")
        self.assertEqual(self.provider.return_value.open.call_count, 2)
        self.assertEqual(runtime.budget_guard.attempted_usage().provider_requests, 2)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertEqual(len(statements), 2 if invalid else 3)
        self.assertEqual({key: self.f.sdk.objects[key] for key in before}, before)
        return result, db

    def test_position_exits_on_complete_synthetic_tape(self):
        result, db = self.advance(invalid=False)
        self.assertEqual(result["account"]["open_position_count"], 0)
        self.assertEqual(result["account"]["closed_position_count"], 1)
        self.assertGreater(result["account"]["realized_closed_net_pnl_usd"], 0)
        self.assertGreater(result["account"]["equity_usd"], 10000)
        step_id = result["coordinator"]["step_id"]
        step = next(json.loads(body) for key, (body, _) in self.f.sdk.objects.items()
                    if key.endswith(f"/live-run-step/{step_id}.json"))
        state_id = step["next_state_id"]
        state = next(json.loads(body) for key, (body, _) in self.f.sdk.objects.items()
                     if key.endswith(f"/live-state/{state_id}.json"))
        checkpoint = state["checkpoint_report"]
        self.assertEqual(checkpoint["account_snapshot"], result["account"])
        records = checkpoint["next_account_input"]["records"]
        self.assertEqual(len(records), 1)
        lifecycle = records[0]["paper_lifecycle_report"]["result"]
        self.assertEqual(lifecycle["status"], "CLOSED")
        self.assertIn(lifecycle["reason"], {"TARGET", "TARGET_GAP"})
        self.assertEqual(lifecycle["raw_exit_price"], 105.0)
        self.assertGreater(lifecycle["exit_price"], 100.0)
        self.assertGreater(lifecycle["exit_fee_usd"], 0)
        self.assertEqual(lifecycle["net_pnl_usd"], result["account"]["realized_closed_net_pnl_usd"])
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloud_paper_budget_reservations WHERE state='SETTLED'"
        ).fetchone()[0], 1)

    def test_invalid_tape_keeps_reservation_for_review(self):
        _, db = self.advance(invalid=True)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloud_paper_budget_reservations WHERE state='RESERVED'"
        ).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
