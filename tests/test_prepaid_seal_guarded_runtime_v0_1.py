from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired, SLOT_MS
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_cloud_paper_composition_v0_1 import FakeClient, MemoryStore, composition

MODULE = "crypto_autopilot.paper.cloud_runtime_v0_3"


class PrepaidSealRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PrepaidD1RuntimeTests(
            "test_meter_readonly_checks_never_debit_or_refresh",
        )
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def runtime(self, **kwargs):
        with patch.object(fixtures, "build_runtime_composition", build_runtime_composition):
            return self.f.runtime(**kwargs)

    def transport(self):
        db = self.f.sqlite()
        size, statements = [1024], []
        def send(request, timeout):
            payload = json.loads(request.data)
            statements.append(payload["sql"])
            cursor = db.execute(payload["sql"], tuple(payload["params"]))
            names = tuple(row[0] for row in cursor.description or ())
            rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
            db.commit()
            size[0] += 64
            return fixtures.Response(fixtures.body(rows=rows, reads=1, writes=7, size=size[0]))
        opener = Mock()
        opener.open.side_effect = send
        return db, size, statements, opener

    def test_disabled_stops_before_prepaid_factory(self):
        with patch(MODULE + ".build_prepaid_runtime") as factory:
            self.assertIsNone(self.runtime(enabled=False))
        factory.assert_not_called()
        self.assertEqual(self.f.sdk.calls, [])

    def test_unshared_ledger_is_rejected(self):
        unshared = composition(FakeClient(), MemoryStore())
        with patch(MODULE + ".build_prepaid_runtime", return_value=unshared):
            with self.assertRaisesRegex(BudgetBlocked, "SHARED_LEDGER_REQUIRED"):
                self.runtime()
        self.assertEqual(unshared.store.calls, [])

    def test_mismatched_or_already_admitted_ledger_is_rejected(self):
        for field, value in (
            ("_writer", "wrong-writer"),
            ("_slot_at_ms", self.f.now + SLOT_MS),
            ("_meter", object()),
            ("_admitted", True),
        ):
            with self.subTest(field=field):
                base = fixtures.build_runtime_composition
                with patch.object(fixtures, "build_runtime_composition", base):
                    prepared = self.f.runtime()
                setattr(prepared.reservation_ledger, field, value)
                self.f.sdk.calls.clear()
                with patch(MODULE + ".build_prepaid_runtime", return_value=prepared):
                    with self.assertRaisesRegex(BudgetBlocked, "RUNTIME_BINDING_MISMATCH"):
                        self.runtime()
                self.assertEqual(self.f.sdk.calls, [])

    def test_shared_admission_continuation_and_reads_are_bound(self):
        db, size, statements, opener = self.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            first = self.runtime()
            report = first.run_slot(
                tick_ms=self.f.now, previous_slot=None, activation_enabled=True,
                run_id="fixture-101",
            )
            self.assertEqual(report["state"], "NO_TRADE")
            self.f.now += SLOT_MS
            self.f._set_run(102)
            self.f.meter = self.f.claim(102)
            self.f.sdk.calls.clear()
            second = self.runtime(database_size=size[0])
            resumed = second.run_slot(
                tick_ms=self.f.now, previous_slot=report["slot_id"],
                activation_enabled=True, run_id="fixture-102",
            )
        self.assertEqual(resumed["account"]["initial_equity_usd"], 10000)
        self.assertEqual(resumed["account"]["open_position_count"], 0)
        self.assertEqual(len(statements), 6)
        self.assertEqual(
            db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0],
            2,
        )
        reads = sum(call["operation"] == "GET" for call in self.f.sdk.calls)
        self.assertEqual(second.budget_guard.attempted_usage().class_b_requests, reads)

    def test_bad_prior_seal_keeps_new_reservation_without_writes_or_settlement(self):
        db, size, statements, opener = self.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            first = self.runtime()
            report = first.run_slot(
                tick_ms=self.f.now, previous_slot=None, activation_enabled=True,
                run_id="fixture-101",
            )
            key = next(k for k in self.f.sdk.objects if "/live-run-result/" in k)
            raw, metadata = self.f.sdk.objects[key]
            changed = json.loads(raw)
            changed["run_id"] = "wrong-run"
            raw = json.dumps(changed, sort_keys=True, separators=(",", ":")).encode()
            self.f.sdk.objects[key] = (raw, {**metadata, "sha256": hashlib.sha256(raw).hexdigest()})
            before = dict(self.f.sdk.objects)
            self.f.now += SLOT_MS
            self.f._set_run(102)
            self.f.meter = self.f.claim(102)
            self.f.sdk.calls.clear()
            second = self.runtime(database_size=size[0])
            with self.assertRaisesRegex(CloudLoopReviewRequired, "COORDINATOR_SEAL_INVALID"):
                second.run_slot(
                    tick_ms=self.f.now, previous_slot=report["slot_id"],
                    activation_enabled=True, run_id="fixture-102",
                )
        self.assertEqual(self.f.sdk.objects, before)
        self.assertFalse(any(call["operation"] == "PUT" for call in self.f.sdk.calls))
        self.assertEqual(len(statements), 5)
        self.assertEqual(
            db.execute("SELECT COUNT(*) FROM cloud_paper_budget_reservations WHERE state='RESERVED'").fetchone()[0],
            1,
        )


if __name__ == "__main__":
    unittest.main()
