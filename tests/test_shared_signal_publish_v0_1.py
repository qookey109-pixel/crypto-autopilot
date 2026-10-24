from __future__ import annotations

import hashlib
import io
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import SharedWriterReservation
from crypto_autopilot.research.shared_signal_publish_v0_1 import (
    NAMESPACE, WRITER, _objects, publish_shared_signal_payload,
)

NOW = 1_800_000_000_000


class Result:
    def __init__(self, rows):
        self.rows = rows


class Meter:
    def charge_before_query(self, **kwargs):
        return "CHARGED"


class MemoryS3:
    def __init__(self):
        self.objects = {}
        self.events = []
        self.fail_key = None
        self.corrupt_key = None
        self.race = False
        self.pointer_race = False
        self.missing_etag = False

    def put_object(self, **kwargs):
        key = kwargs["Key"]
        self.events.append(("put", key))
        if self.fail_key == key:
            raise RuntimeError("SECRET raw provider response")
        if key.endswith("/latest.json") and self.pointer_race:
            self.objects[key] = b"newer concurrent pointer"
        if "IfMatch" in kwargs and kwargs["IfMatch"] != (
            '"' + hashlib.sha256(self.objects.get(key, b"")).hexdigest() + '"'
        ):
            raise RuntimeError("precondition failed")
        if kwargs.get("IfNoneMatch") == "*" and (self.race or key in self.objects):
            raise RuntimeError("precondition failed")
        self.objects[key] = kwargs["Body"]
        return {"ETag": "fixture"}

    def get_object(self, **kwargs):
        key = kwargs["Key"]
        self.events.append(("get", key))
        if key not in self.objects:
            error = RuntimeError("missing")
            error.response = {"ResponseMetadata": {"HTTPStatusCode": 404}}
            raise error
        body = self.objects[key]
        if key == self.corrupt_key:
            body += b"changed"
        return {"Body": io.BytesIO(body),
                "ETag": None if self.missing_etag else '"' + hashlib.sha256(body).hexdigest() + '"',
                "Metadata": {"sha256": hashlib.sha256(body).hexdigest()}}


class SharedSignalPublisherTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "schema": "research-signal-layer-run-v0.2", "mode": "RESEARCH_ONLY",
            "run_id": "123", "generated_at_utc": "2027-01-15T08:00:00Z",
            "source_snapshots": [], "kol_forecasts": [],
            "authority": {"automatic_model_promotion": False,
                          "direct_trade_trigger": False,
                          "real_money_order": False, "live_trading": False},
        }
        self.backend = MemoryS3()
        self.events = []
        snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=NOW, measured_through_ms=NOW, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        self.guard = CloudBudgetGuard(snapshot=snapshot, clock_ms=lambda: NOW)
        self.reservation = SharedWriterReservation(
            writer_id=WRITER, slot_id=f"slot:{NOW}", idempotency_key=f"slot:{NOW}",
            slot_at_ms=NOW, reserved_at_ms=NOW, provider_requests=0,
            r2_class_a=3, r2_class_b=6,
            r2_new_bytes=sum(len(body) for _, body in _objects(self.payload, "123")),
            d1_queries=4, d1_rows_read=100, d1_rows_written=10,
            d1_storage_growth_bytes=100,
        )
        self.query_rows = ({"writer_id": WRITER, "slot_id": f"slot:{NOW}"},)
        self.factory = patch.object(BudgetedR2Store, "from_credentials",
                                    side_effect=self.make_store)
        self.mock_factory = self.factory.start()
        self.addCleanup(self.factory.stop)

    def make_store(self, **kwargs):
        self.events.append("construct")
        self.assertIn("query", self.events)
        return BudgetedR2Store(client=self.backend, bucket=kwargs["bucket"],
                               before_external=kwargs["before_external"])

    def execute(self, sql, params):
        self.events.append("query")
        return Result(self.query_rows)

    def publish(self, **overrides):
        args = dict(
            payload=self.payload, run_id="123", reservation=self.reservation,
            guard=self.guard, execute=self.execute, query_meter=Meter(),
            validate_binding=lambda: self.events.append("binding"),
            credentials=dict(account_id="fixture", bucket="fixture",
                             access_key_id="fixture", secret_access_key="fixture"),
            execution_enabled=True,
        )
        args.update(overrides)
        return publish_shared_signal_payload(**args)

    def test_default_disabled_before_credentials_and_queries(self):
        result = self.publish(execution_enabled=False, credentials={})
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.events, [])
        self.mock_factory.assert_not_called()

    def test_admission_then_three_writes_six_reads_and_latest_last(self):
        result = self.publish()
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(result["objects_verified"], 3)
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 3)
        self.assertEqual(result["attempted_usage"]["r2_class_b"], 6)
        self.assertEqual(result["bucket_scans_performed"], 0)
        self.assertFalse(result["paper_activation_allowed"])
        keys = [key for key, _ in _objects(self.payload, "123")]
        self.assertEqual(self.backend.events, [
            ("get", keys[2]),
            ("get", keys[0]), ("put", keys[0]), ("get", keys[0]),
            ("get", keys[1]), ("put", keys[1]), ("get", keys[1]),
            ("put", keys[2]), ("get", keys[2]),
        ])

    def test_bad_binding_or_envelope_blocks_before_query(self):
        for reservation in (
            replace(self.reservation, writer_id="unknown"),
            replace(self.reservation, r2_class_a=2),
            replace(self.reservation, provider_requests=1),
            replace(self.reservation, r2_new_bytes=0),
        ):
            with self.subTest(reservation=reservation), self.assertRaises(BudgetBlocked):
                self.publish(reservation=reservation)
        self.assertEqual(self.events, [])
        self.mock_factory.assert_not_called()

    def test_unknown_coverage_blocks_before_query(self):
        self.guard.snapshot = replace(self.guard.snapshot, reservation_coverage_complete=False)
        with self.assertRaises(BudgetBlocked):
            self.publish()
        self.assertNotIn("query", self.events)
        self.mock_factory.assert_not_called()

    def test_rejected_admission_does_not_construct_store(self):
        self.query_rows = ()
        with self.assertRaises(BudgetBlocked):
            self.publish()
        self.mock_factory.assert_not_called()

    def test_immutable_conflict_does_not_publish_pointer(self):
        key = _objects(self.payload, "123")[0][0]
        self.backend.objects[key] = b"conflicting"
        result = self.publish()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["latest_pointer_verified"])
        self.assertEqual(self.backend.events, [("get", f"{NAMESPACE}/latest.json"), ("get", key)])

    def test_partial_write_and_readback_failure_preserve_evidence(self):
        keys = [key for key, _ in _objects(self.payload, "123")]
        self.backend.corrupt_key = keys[1]
        result = self.publish()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["objects_verified"], 1)
        self.assertNotIn(keys[2], self.backend.objects)
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 2)
        self.assertTrue(result["central_reservation_retained"])

    def test_failed_latest_is_not_retried_and_no_exception_text_leaks(self):
        self.backend.fail_key = f"{NAMESPACE}/latest.json"
        result = self.publish()
        self.assertEqual(result["objects_verified"], 2)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 3)
        self.assertFalse(result["automatic_retry_allowed"])
        self.assertNotIn("SECRET", str(result))

    def test_conditional_immutable_write_conflict_stops_publication(self):
        self.backend.race = True
        result = self.publish()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["objects_verified"], 0)
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 1)
        self.assertNotIn(f"{NAMESPACE}/latest.json", self.backend.objects)

    def test_identical_existing_objects_are_verified_without_rewriting(self):
        for key, body in _objects(self.payload, "123")[:2]:
            self.backend.objects[key] = body
        result = self.publish()
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 1)
        self.assertEqual(result["attempted_usage"]["r2_class_b"], 6)

    def test_invalid_run_or_promoted_payload_never_queries(self):
        with self.assertRaises(BudgetBlocked):
            self.publish(run_id="../123")
        self.payload["authority"]["live_trading"] = True
        with self.assertRaises(BudgetBlocked):
            self.publish()
        self.assertEqual(self.events, [])


    def previous_pointer(self, timestamp="2027-01-15T07:59:00Z"):
        pointer = json.loads(_objects(self.payload, "123")[2][1])
        pointer["run_id"] = "122"
        pointer["manifest_key"] = f"{NAMESPACE}/runs/run=122/manifest.json"
        pointer["generated_at_utc"] = timestamp
        body = json.dumps(pointer).encode()
        self.backend.objects[f"{NAMESPACE}/latest.json"] = body
        return body

    def test_newer_payload_replaces_older_pointer_conditionally(self):
        self.previous_pointer()
        result = self.publish()
        self.assertEqual(result["status"], "PUBLISHED")
        pointer = json.loads(self.backend.objects[f"{NAMESPACE}/latest.json"])
        self.assertEqual(pointer["run_id"], "123")

    def test_equal_or_newer_pointer_stops_before_any_write(self):
        for timestamp in ("2027-01-15T08:00:00Z", "2027-01-15T09:00:00Z"):
            with self.subTest(timestamp=timestamp):
                self.backend.events.clear()
                previous = self.previous_pointer(timestamp)
                result = self.publish()
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["stage"], "LATEST_POINTER_PREFLIGHT")
                self.assertEqual(result["attempted_usage"]["r2_class_a"], 0)
                self.assertEqual(self.backend.objects[f"{NAMESPACE}/latest.json"], previous)

    def test_concurrent_pointer_change_is_not_overwritten_or_retried(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                self.backend.objects.clear()
                self.backend.events.clear()
                # Fresh local guard for this independent simulated run.
                self.guard = CloudBudgetGuard(snapshot=self.guard.snapshot, clock_ms=lambda: NOW)
                if existing:
                    self.previous_pointer()
                self.backend.pointer_race = True
                result = self.publish()
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["objects_verified"], 2)
                self.assertEqual(self.backend.objects[f"{NAMESPACE}/latest.json"],
                                 b"newer concurrent pointer")
                puts = [event for event in self.backend.events
                        if event == ("put", f"{NAMESPACE}/latest.json")]
                self.assertEqual(len(puts), 1)

    def test_missing_etag_or_malformed_pointer_prevents_write(self):
        self.previous_pointer()
        self.backend.missing_etag = True
        result = self.publish()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 0)
        self.backend.missing_etag = False
        self.backend.objects[f"{NAMESPACE}/latest.json"] = b"null"
        result = self.publish()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 0)

    def test_oversized_pointer_prevents_write(self):
        self.backend.objects[f"{NAMESPACE}/latest.json"] = b" " * 2_500_001
        result = self.publish()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["attempted_usage"]["r2_class_a"], 0)

    def test_timestamp_requires_explicit_utc_instant_before_query(self):
        for value in ("2027-01-15", "2027-01-15Z", "2027-01-15T08:00:00", "badZ"):
            self.payload["generated_at_utc"] = value
            with self.subTest(value=value), self.assertRaises(BudgetBlocked):
                self.publish()
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
