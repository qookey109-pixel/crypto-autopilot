"""Offline tests for authenticated run binding to the prepared PAPER runtime."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import AllocationEvidence
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_paper_v05_prepaid_runtime_v0_1 import PaperV05RuntimeTests

try:
    from crypto_autopilot.paper.run_bound_paper_runtime_v0_1 import (
        build_bound_runtime, claim_bound_meter,
    )
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.run_bound_paper_runtime_v0_1":
        raise
    build_bound_runtime = claim_bound_meter = None


class RunBoundPaperTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(claim_bound_meter)
        self.outer = PaperV05RuntimeTests("test_default_disabled_has_no_requests")
        self.outer.setUp()
        self.addCleanup(self.outer.doCleanups)
        self.f = self.outer.f
        self.f._set_run(102)

    def claim(self, enabled=True):
        now = self.f.now
        return claim_bound_meter(
            authority_document=self.f.authority, writer_id=fixtures.WRITER,
            slot_id=f"slot:{now}", run_id=102, transport=self.f.github,
            evidence=AllocationEvidence(
                account_coverage_complete=True, zero_cost_verified=True,
                observed_at_ms=now, measured_through_ms=now,
                available={"queries": 1000, "rows_read": 1_000_000,
                           "rows_written": 10_000, "storage_bytes": 10_000_000},
            ),
            clock_ms=lambda: self.f.now, execution_enabled=enabled,
        )

    def runtime(self, bound):
        self.f.meter = bound.meter
        def build(**kwargs):
            kwargs.pop("query_meter")
            kwargs["clock_ms"] = bound.meter._clock_ms
            return build_bound_runtime(bound=bound, **kwargs)
        with patch.object(fixtures, "build_runtime_composition", build):
            return self.f.runtime()

    def test_disabled_claim_has_no_github_requests(self):
        before = list(self.f.github.calls)
        with self.assertRaises(BudgetBlocked):
            self.claim(enabled=False)
        self.assertEqual(self.f.github.calls, before)

    def test_cannot_forge_bound_meter_using_unverified_fields(self):
        from crypto_autopilot.paper.run_bound_paper_runtime_v0_1 import RunBoundMeter
        with self.assertRaises((BudgetBlocked, TypeError)):
            RunBoundMeter(meter=self.f.meter, run_id=102, writer_id=fixtures.WRITER,
                          slot_id=f"slot:{self.f.now}")
        self.assertEqual(self.f.sdk.calls, [])

    def test_run_mismatch_stops_before_d1_or_r2_then_exact_run_succeeds(self):
        bound = self.claim()
        runtime = self.runtime(bound)
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as opener:
            with self.assertRaises(BudgetBlocked):
                runtime.run_slot(tick_ms=self.f.now, previous_slot=None,
                                 activation_enabled=True, run_id="101")
        opener.assert_not_called()
        self.assertEqual(self.f.sdk.calls, [])
        self.assertEqual(bound.meter.report()["query_attempts_charged"], 0)
        db, _, statements, fake_opener = self.outer.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=fake_opener):
            result = runtime.run_slot(tick_ms=self.f.now, previous_slot=None,
                                      activation_enabled=True, run_id="102")
        self.assertEqual(result["state"], "NO_TRADE")
        self.assertEqual(len(statements), 3)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
