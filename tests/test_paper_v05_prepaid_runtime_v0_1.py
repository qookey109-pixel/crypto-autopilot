"""Synthetic V0.5 shared admission through existing seal-guarded Paper runtime."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import RESERVE_SHARED_WRITER_SQL as OLD_SQL
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL as NEW_SQL
import test_prepaid_d1_runtime_v0_1 as fixtures
import test_prepaid_seal_guarded_runtime_v0_1 as seal_fixtures

try:
    from crypto_autopilot.paper.cloud_runtime_v0_4 import build_runtime_composition
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.cloud_runtime_v0_4":
        raise
    build_runtime_composition = None


class PaperV05RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(build_runtime_composition)
        self.outer = seal_fixtures.PrepaidSealRuntimeTests("test_disabled_stops_before_prepaid_factory")
        self.outer.setUp()
        self.addCleanup(self.outer.doCleanups)
        self.f = self.outer.f

    def runtime(self, **kwargs):
        def same_clock(**params):
            params["clock_ms"] = params["query_meter"]._clock_ms
            return build_runtime_composition(**params)
        with patch.object(seal_fixtures, "build_runtime_composition", same_clock):
            return self.outer.runtime(**kwargs)

    def test_default_disabled_has_no_requests(self):
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
            self.assertIsNone(self.runtime(enabled=False))
        network.assert_not_called()
        self.assertEqual(self.f.sdk.calls, [])

    def test_different_meter_clock_is_rejected_before_clients(self):
        with patch.object(seal_fixtures, "build_runtime_composition", build_runtime_composition):
            with self.assertRaisesRegex(BudgetBlocked, "CLOCK"):
                self.outer.runtime()
        self.assertEqual(self.f.sdk.calls, [])

    def test_external_io_before_shared_admission_is_blocked(self):
        runtime = self.runtime()
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
            with self.assertRaises(BudgetBlocked):
                runtime.store.list_json_ids("live-run-result")
            with self.assertRaises(BudgetBlocked):
                runtime.client._get_json("/api/v1/market/depth", {})
        self.assertEqual(self.f.sdk.calls, [])
        network.assert_not_called()
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)

    def test_direct_provider_attempts_are_metered_after_admission(self):
        runtime = self.runtime()
        runtime.reservation_ledger._admitted = True  # synthetic admitted envelope only
        with patch("crypto_autopilot.paper.cloud_pionex_client_v0_1.build_opener") as factory, patch(
            "crypto_autopilot.paper.cloud_pionex_client_v0_1.CloudPaperPionexPublicClient._pace"
        ):
            response = factory.return_value.open.return_value.__enter__.return_value
            response.getcode.return_value = 200
            response.headers = {}
            response.read.return_value = b'{"result": true, "data": {}}'
            for _ in range(18):
                runtime.client._get_json("/api/v1/market/depth", {})
            with self.assertRaises(BudgetBlocked):
                runtime.client._get_json("/api/v1/market/depth", {})
        self.assertEqual(factory.return_value.open.call_count, 18)
        self.assertEqual(runtime.budget_guard.attempted_usage().provider_requests, 18)

    def test_two_no_trade_slots_use_v05_and_recover_account(self):
        db, size, statements, opener = self.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            first = self.runtime()
            report = first.run_slot(tick_ms=self.f.now, previous_slot=None,
                                    activation_enabled=True, run_id="fixture-101")
            self.assertEqual(report["state"], "NO_TRADE")
            calls_after_settlement = list(self.f.sdk.calls)
            with self.assertRaises(BudgetBlocked):
                first.store.list_json_ids("live-run-result")
            self.assertEqual(self.f.sdk.calls, calls_after_settlement)
            with self.assertRaises(BudgetBlocked):
                first.run_slot(tick_ms=self.f.now, previous_slot=None,
                               activation_enabled=True, run_id="duplicate")
            self.f.now += SLOT_MS
            self.f._set_run(102)
            self.f.meter = self.f.claim(102)
            second = self.runtime(database_size=size[0])
            resumed = second.run_slot(tick_ms=self.f.now, previous_slot=report["slot_id"],
                                      activation_enabled=True, run_id="fixture-102")
        self.assertEqual(resumed["state"], "NO_TRADE")
        self.assertEqual(resumed["account"]["initial_equity_usd"], 10000)
        self.assertEqual(statements.count(NEW_SQL), 2)
        self.assertNotIn(OLD_SQL, statements)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 2)

    def test_lost_admission_response_stops_before_r2(self):
        db, _, _, _ = self.outer.transport()
        def lost(request, timeout):
            import json
            payload = json.loads(request.data)
            db.execute(payload["sql"], tuple(payload["params"])).fetchall()
            db.commit()
            raise OSError("synthetic ambiguous response")
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
            network.return_value.open.side_effect = lost
            runtime = self.runtime()
            with self.assertRaises(BudgetBlocked):
                runtime.run_slot(tick_ms=self.f.now, previous_slot=None,
                                 activation_enabled=True, run_id="fixture-101")
        self.assertEqual(self.f.sdk.calls, [])
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 2)


if __name__ == "__main__":
    unittest.main()
