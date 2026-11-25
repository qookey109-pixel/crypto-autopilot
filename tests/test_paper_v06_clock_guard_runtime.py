"""Synthetic Paper successor integration for the V0.6 shared clock guard."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_runtime_v0_5 import build_runtime_composition
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
import test_prepaid_d1_runtime_v0_1 as fixtures
import test_prepaid_seal_guarded_runtime_v0_1 as seal_fixtures


class PaperV06RuntimeTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            blocker = patch(target, side_effect=AssertionError("unexpected network access"))
            blocker.start()
            self.addCleanup(blocker.stop)
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

    def test_disabled_has_no_network_or_storage(self):
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
            self.assertIsNone(self.runtime(enabled=False))
        network.assert_not_called()
        self.assertEqual(self.f.sdk.calls, [])

    def test_successful_admission_keeps_normal_no_trade(self):
        db, _, statements, opener = self.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            runtime = self.runtime()
            report = runtime.run_slot(tick_ms=self.f.now, previous_slot=None,
                                      activation_enabled=True, run_id="fixture-101")
        self.assertEqual(report["state"], "NO_TRADE")
        self.assertEqual(statements.count(RESERVE_SHARED_WRITER_SQL), 1)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)

    def test_rollback_after_shared_insert_stops_before_storage_and_provider(self):
        db, _, statements, opener = self.outer.transport()
        original_send = opener.open.side_effect
        slot = self.f.now
        runtime = self.runtime()
        self.f.now = slot + 100
        def clock_back_after_commit(request, timeout):
            response = original_send(request, timeout)
            if statements[-1] == RESERVE_SHARED_WRITER_SQL:
                self.f.now = slot + 50
            return response
        opener.open.side_effect = clock_back_after_commit
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener), patch(
            "crypto_autopilot.paper.cloud_pionex_client_v0_1.build_opener"
        ) as provider:
            with self.assertRaises(BudgetBlocked):
                runtime.run_slot(tick_ms=slot, previous_slot=None,
                                 activation_enabled=True, run_id="fixture-101")
        provider.assert_not_called()
        self.assertEqual(self.f.sdk.calls, [])
        self.assertEqual(statements.count(RESERVE_SHARED_WRITER_SQL), 1)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertGreater(self.f.meter.report()["query_attempts_charged"], 0)

    def test_two_slots_preserve_account_continuity(self):
        db, size, statements, opener = self.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            first = self.runtime()
            report = first.run_slot(tick_ms=self.f.now, previous_slot=None,
                                    activation_enabled=True, run_id="fixture-101")
            self.f.now += SLOT_MS
            self.f._set_run(102)
            self.f.meter = self.f.claim(102)
            second = self.runtime(database_size=size[0])
            resumed = second.run_slot(tick_ms=self.f.now, previous_slot=report["slot_id"],
                                      activation_enabled=True, run_id="fixture-102")
        self.assertEqual(report["state"], "NO_TRADE")
        self.assertEqual(resumed["state"], "NO_TRADE")
        self.assertEqual(resumed["account"]["initial_equity_usd"], 10000)
        self.assertEqual(statements.count(RESERVE_SHARED_WRITER_SQL), 2)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 2)
