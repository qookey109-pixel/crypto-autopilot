from __future__ import annotations

import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    LivePaperRunCoordinatorPolicy, coordinate_live_paper_run_step,
)
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import SharedWriterReservation
from test_live_paper_run_recovery_v0_1 import _Feed, _bootstrap_state
from test_shared_signal_publish_v0_1 import MemoryS3, Meter, NOW, Result

try:
    from crypto_autopilot.paper.shared_run_recovery_v0_1 import run_shared_run_recovery
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.shared_run_recovery_v0_1":
        raise
    run_shared_run_recovery = None

PREFIX = "paper-run-store/v0.1"


class RecoveryS3(MemoryS3):
    def __init__(self):
        super().__init__()
        self.truncated = False
        self.after_call = lambda: None

    def list_objects_v2(self, **kwargs):
        self.events.append(("list", kwargs["Prefix"]))
        self.after_call()
        keys = sorted(key for key in self.objects if key.startswith(kwargs["Prefix"]))
        limit = kwargs["MaxKeys"]
        return {"Contents": [{"Key": key} for key in keys[:limit]],
                "IsTruncated": self.truncated or len(keys) > limit,
                "NextContinuationToken": "next"}


class SharedRunRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(run_shared_run_recovery),
                        "shared-admitted recovery composition is missing")
        self.clock = [NOW]
        self.backend = RecoveryS3()
        state, spec = _bootstrap_state()
        store = R2PaperRunStore(BudgetedR2Store(
            client=self.backend, bucket="fixture", before_external=lambda *args: None))
        self.committed = coordinate_live_paper_run_step(
            run_name="shared-recovery", tick_time_ms=5000, candidate_specs=(spec,),
            feed=_Feed(5000), store=store, initial_state=state,
            policy=LivePaperRunCoordinatorPolicy(compact_tick_reference=True))
        self.backend.events.clear()
        self.claimed = False
        self.query_count = 0
        self.snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=NOW, measured_through_ms=NOW, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0)
        self.guard = CloudBudgetGuard(snapshot=self.snapshot, clock_ms=lambda: self.clock[0])
        self.reservation = SharedWriterReservation(
            writer_id="crypto-autopilot:live-paper-run-recovery-v0-1",
            slot_id=f"slot:{NOW}", idempotency_key=f"slot:{NOW}",
            slot_at_ms=NOW, reserved_at_ms=NOW, provider_requests=0,
            r2_class_a=8, r2_class_b=64, r2_new_bytes=16384,
            d1_queries=4, d1_rows_read=100, d1_rows_written=10,
            d1_storage_growth_bytes=100)
        self.factory = patch.object(BudgetedR2Store, "from_credentials",
                                    side_effect=self.make_store)
        self.mock_factory = self.factory.start()
        self.addCleanup(self.factory.stop)

    def make_store(self, **kwargs):
        self.assertTrue(self.claimed)
        self.assertEqual(kwargs["policy"].maximum_list_pages, 1)
        self.assertEqual(kwargs["policy"].maximum_list_keys_per_page, 4)
        return BudgetedR2Store(client=self.backend, bucket=kwargs["bucket"],
                               before_external=kwargs["before_external"], policy=kwargs["policy"])

    def execute(self, sql, params):
        self.query_count += 1
        if "INSERT INTO" in sql:
            if not self.claimed:
                self.claimed = True
                return Result(({"writer_id": self.reservation.writer_id,
                                "slot_id": self.reservation.slot_id},))
            return Result(())
        row = asdict(self.reservation)
        row["utc_day"] = self.reservation.utc_day
        return Result((row,))

    def key(self, kind, identity):
        return f"{PREFIX}/{kind}/{identity}.json"

    def remove_seal(self):
        step = self.committed["run_step"]
        key = self.key("live-run-result", step["request_id"])
        del self.backend.objects[key]
        return key

    def run_recovery(self, **overrides):
        args = dict(
            run_id=self.committed["run_id"], reservation=self.reservation,
            guard=self.guard, execute=self.execute, query_meter=Meter(),
            validate_binding=lambda: None,
            credentials=dict(account_id="fixture", bucket="fixture",
                             access_key_id="fixture", secret_access_key="fixture"),
            repair_missing_result_seals=True, execution_enabled=True)
        args.update(overrides)
        return run_shared_run_recovery(**args)

    def test_disabled_does_not_read_credentials_or_admit(self):
        got = self.run_recovery(execution_enabled=False, credentials={})
        self.assertEqual(got["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.query_count, 0)
        self.assertEqual(self.backend.events, [])
        self.mock_factory.assert_not_called()

    def test_consistent_audit_does_not_write(self):
        got = self.run_recovery(repair_missing_result_seals=False)
        self.assertEqual(got["state"], "RUN_CONSISTENT")
        self.assertEqual(got["provider_requests_performed"], 0)
        self.assertEqual(got["attempted_usage"]["r2_class_a"], 4)
        self.assertFalse(any(kind == "put" for kind, _ in self.backend.events))

    def test_compact_missing_seal_repairs_only_result_and_reads_it_back(self):
        key = self.remove_seal()
        before = dict(self.backend.objects)
        got = self.run_recovery()
        self.assertEqual(got["state"], "MISSING_RESULT_SEALS_REPAIRED")
        self.assertEqual(got["result_seal_writes_performed"], 1)
        self.assertEqual(set(self.backend.objects) - set(before), {key})
        self.assertEqual({k: self.backend.objects[k] for k in before}, before)
        write_index = self.backend.events.index(("put", key))
        self.assertTrue(all(event == ("get", key)
                            for event in self.backend.events[write_index + 1:]))
        self.assertGreater(len(self.backend.events[write_index + 1:]), 0)
        self.assertEqual(got["attempted_usage"]["r2_class_a"], 5)
        self.assertTrue(got["central_reservation_retained"])

    def test_missing_tick_cannot_repair(self):
        self.remove_seal()
        del self.backend.objects[self.key("live-tick", self.committed["run_step"]["tick_id"])]
        got = self.run_recovery()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["result_seal_writes_performed"], 0)
        self.assertFalse(any(kind == "put" for kind, _ in self.backend.events))

    def test_truncated_inventory_is_not_partial_success(self):
        self.remove_seal()
        self.backend.truncated = True
        got = self.run_recovery()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["result_seal_writes_performed"], None)
        self.assertFalse(any(kind == "put" for kind, _ in self.backend.events))

    def test_concurrent_create_cannot_overwrite_or_retry(self):
        key = self.remove_seal()
        self.backend.race = True
        got = self.run_recovery()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertNotIn(key, self.backend.objects)
        self.assertEqual(self.backend.events.count(("put", key)), 1)
        self.assertEqual(got["attempted_usage"]["r2_class_a"], 5)

    def test_write_failure_retains_usage_without_raw_error(self):
        key = self.remove_seal()
        self.backend.fail_key = key
        got = self.run_recovery()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertNotIn("SECRET", str(got))
        self.assertTrue(got["central_reservation_retained"])
        self.assertEqual(got["attempted_usage"]["r2_class_a"], 5)

    def test_expiry_after_first_list_prevents_more_access_or_writes(self):
        self.remove_seal()
        self.backend.after_call = lambda: self.clock.__setitem__(0, NOW + 60001)
        got = self.run_recovery()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(sum(kind == "list" for kind, _ in self.backend.events), 1)
        self.assertFalse(any(kind == "put" for kind, _ in self.backend.events))

    def test_reconstructed_duplicate_does_not_construct_or_access(self):
        self.run_recovery()
        before = list(self.backend.events)
        self.mock_factory.reset_mock()
        guard = CloudBudgetGuard(snapshot=self.snapshot, clock_ms=lambda: NOW)
        with self.assertRaises(BudgetBlocked):
            self.run_recovery(guard=guard)
        self.assertEqual(self.backend.events, before)
        self.mock_factory.assert_not_called()

    def test_invalid_envelope_or_unknown_coverage_precedes_admission(self):
        for changes in (dict(writer_id="unknown"), dict(provider_requests=1),
                        dict(r2_class_a=7), dict(r2_class_b=63), dict(r2_new_bytes=0)):
            with self.subTest(changes=changes), self.assertRaises(BudgetBlocked):
                self.run_recovery(reservation=replace(self.reservation, **changes))
        self.guard.snapshot = replace(self.snapshot, reservation_coverage_complete=False)
        with self.assertRaises(BudgetBlocked):
            self.run_recovery()
        self.assertEqual(self.query_count, 0)
        self.mock_factory.assert_not_called()

    def test_legacy_embedded_tick_step_still_repairs(self):
        # Regenerate only the fixture; this never invokes an external transport.
        self.backend = RecoveryS3()
        state, spec = _bootstrap_state()
        store = R2PaperRunStore(BudgetedR2Store(
            client=self.backend, bucket="fixture", before_external=lambda *args: None))
        self.committed = coordinate_live_paper_run_step(
            run_name="shared-recovery", tick_time_ms=5000, candidate_specs=(spec,),
            feed=_Feed(5000), store=store, initial_state=state)
        self.backend.events.clear()
        self.remove_seal()
        got = self.run_recovery()
        self.assertEqual(got["state"], "MISSING_RESULT_SEALS_REPAIRED")
        self.assertEqual(got["result_seal_writes_performed"], 1)


if __name__ == "__main__":
    unittest.main()
