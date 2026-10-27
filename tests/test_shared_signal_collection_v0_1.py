from __future__ import annotations

import io
import json
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import SharedWriterReservation
from test_shared_signal_publish_v0_1 import MemoryS3, Meter, NOW, Result

try:
    from crypto_autopilot.research.shared_signal_collection_v0_1 import (
        run_shared_signal_collection,
    )
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.research.shared_signal_collection_v0_1":
        raise
    run_shared_signal_collection = None

SOURCES = json.loads(
    (Path(__file__).resolve().parents[1] / "config/research_signal_layer_v0_2.json")
    .read_text(encoding="utf-8")
)["sources"]


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


class SharedSignalCollectionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(run_shared_signal_collection),
                        "combined shared-admitted source/publication runtime is missing")
        self.clock = [NOW]
        self.events = []
        self.backend = MemoryS3()
        self.claimed = False
        self.source_error = False
        self.expire_after_source = False
        self.body = json.dumps({"title": "public fixture"}).encode()
        self.snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=NOW, measured_through_ms=NOW, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        self.guard = CloudBudgetGuard(snapshot=self.snapshot, clock_ms=lambda: self.clock[0])
        self.reservation = SharedWriterReservation(
            writer_id="crypto-autopilot:research-signal-layer-v0-2",
            slot_id=f"slot:{NOW}", idempotency_key=f"slot:{NOW}",
            slot_at_ms=NOW, reserved_at_ms=NOW, provider_requests=3,
            r2_class_a=3, r2_class_b=6, r2_new_bytes=270336,
            d1_queries=4, d1_rows_read=100, d1_rows_written=10,
            d1_storage_growth_bytes=100,
        )
        self.factory = patch.object(BudgetedR2Store, "from_credentials",
                                    side_effect=self.make_store)
        self.mock_factory = self.factory.start()
        self.addCleanup(self.factory.stop)

    def execute(self, sql, params):
        self.events.append("admission_query")
        if "INSERT INTO" in sql:
            if not self.claimed:
                self.claimed = True
                return Result(({"writer_id": self.reservation.writer_id,
                                "slot_id": self.reservation.slot_id},))
            return Result(())
        row = asdict(self.reservation)
        row["utc_day"] = self.reservation.utc_day
        return Result((row,))

    def transport(self, request, *, timeout):
        self.assertIn("admission_query", self.events)
        self.assertEqual(timeout, 20)
        self.assertEqual(request.get_method(), "GET")
        self.events.append("source")
        if self.source_error:
            raise RuntimeError("SECRET raw transport diagnostic")
        if self.expire_after_source:
            self.clock[0] += 60_001
        return Response(self.body)

    def make_store(self, **kwargs):
        self.events.append("construct_store")
        self.assertEqual(self.events.count("source"), 3)
        return BudgetedR2Store(client=self.backend, bucket=kwargs["bucket"],
                               before_external=kwargs["before_external"])

    def run_cycle(self, **overrides):
        args = dict(
            sources=SOURCES, run_id="123", reservation=self.reservation,
            guard=self.guard, execute=self.execute, query_meter=Meter(),
            validate_binding=lambda: None,
            credentials=dict(account_id="fixture", bucket="fixture",
                             access_key_id="fixture", secret_access_key="fixture"),
            transport=self.transport, execution_enabled=True,
        )
        args.update(overrides)
        return run_shared_signal_collection(**args)

    def test_disabled_and_no_enabled_sources_have_no_side_effects(self):
        got = self.run_cycle(execution_enabled=False, credentials={})
        self.assertEqual(got["status"], "SKIPPED_DISABLED")
        got = self.run_cycle(sources=[dict(row, enabled=False) for row in SOURCES])
        self.assertEqual(got["status"], "SKIPPED_NO_ENABLED_SOURCES")
        self.assertEqual(self.events, [])
        self.mock_factory.assert_not_called()

    def test_one_admission_covers_all_sources_then_conditional_publication(self):
        got = self.run_cycle()
        self.assertEqual(got["status"], "PUBLISHED")
        self.assertEqual(self.events[:4], ["admission_query", "source", "source", "source"])
        self.assertEqual(self.events.count("admission_query"), 1)
        self.assertEqual(got["provider_requests_performed"], 3)
        self.assertEqual(got["attempted_usage"]["r2_class_a"], 3)
        self.assertEqual(got["attempted_usage"]["r2_class_b"], 6)
        self.assertTrue(got["central_reservation_retained"])
        self.assertFalse(got["paper_activation_allowed"])
        pointer = json.loads(self.backend.objects["research/signal-layer/v0-2/latest.json"])
        self.assertEqual(pointer["run_id"], "123")

    def test_duplicate_reconstruction_stops_before_any_new_source_request(self):
        self.run_cycle()
        before = list(self.backend.events)
        new_guard = CloudBudgetGuard(snapshot=self.snapshot, clock_ms=lambda: NOW)
        with self.assertRaises(BudgetBlocked):
            self.run_cycle(guard=new_guard)
        self.assertEqual(self.events.count("source"), 3)
        self.assertEqual(self.backend.events, before)

    def test_unknown_coverage_prevents_admission_and_sources(self):
        self.guard.snapshot = replace(self.snapshot, reservation_coverage_complete=False)
        with self.assertRaises(BudgetBlocked):
            self.run_cycle()
        self.assertEqual(self.events, [])

    def test_source_failure_stops_without_retry_or_error_value_leak(self):
        self.source_error = True
        got = self.run_cycle()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["stage"], "SOURCE_ACQUISITION")
        self.assertEqual(got["provider_requests_performed"], 1)
        self.assertTrue(got["central_reservation_retained"])
        self.assertNotIn("SECRET", str(got))
        self.mock_factory.assert_not_called()

    def test_expired_evidence_stops_before_second_source_and_s3(self):
        self.expire_after_source = True
        got = self.run_cycle()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["provider_requests_performed"], 1)
        self.mock_factory.assert_not_called()

    def test_unregistered_duplicate_sources_and_wrong_envelope_precede_admission(self):
        bad = [dict(SOURCES[0], url="https://unregistered.invalid")]
        for sources in (bad, [SOURCES[0], SOURCES[0]]):
            with self.subTest(sources=sources), self.assertRaises(BudgetBlocked):
                self.run_cycle(sources=sources)
        with self.assertRaises(BudgetBlocked):
            self.run_cycle(reservation=replace(self.reservation, provider_requests=2))
        self.assertEqual(self.events, [])

    def test_oversized_publication_retains_envelope_without_s3(self):
        self.body = json.dumps({"title": "x" * 300000}).encode()
        got = self.run_cycle()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["stage"], "PAYLOAD_BOUNDS")
        self.assertEqual(got["provider_requests_performed"], 3)
        self.mock_factory.assert_not_called()

    def test_default_transport_rejects_redirects(self):
        from crypto_autopilot.research.shared_signal_collection_v0_1 import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))

    def test_immutable_conflict_retains_admission_and_stops_pointer(self):
        self.backend.objects["research/signal-layer/v0-2/runs/run=123/signals.json"] = b"conflict"
        got = self.run_cycle()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["provider_requests_performed"], 3)
        self.assertNotIn("research/signal-layer/v0-2/latest.json", self.backend.objects)


    def test_cross_source_forecast_id_revision_stops_before_s3(self):
        self.body = json.dumps({
            "forecasts": [{
                "forecast_id": "same-id", "symbol": "BTC_USDT_PERP",
                "direction": "long", "confidence": 0.5,
                "published_at_ms": NOW - 1000, "target_time_ms": NOW + 60000,
            }],
        }).encode()
        got = self.run_cycle()
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.mock_factory.assert_not_called()



    def test_malformed_declared_json_stops_before_s3(self):
        for body in (b"{broken", b"[]", b'{"forecasts":null}', b'{"forecasts":{}}'):
            with self.subTest(body=body):
                self.claimed = False
                self.events.clear()
                self.backend = MemoryS3()
                self.guard = CloudBudgetGuard(
                    snapshot=self.snapshot, clock_ms=lambda: self.clock[0])
                self.mock_factory.reset_mock()
                self.body = body
                got = self.run_cycle()
                self.assertEqual(got["status"], "REVIEW_REQUIRED")
                self.assertEqual(got["stage"], "SOURCE_ACQUISITION")
                self.assertEqual(got["provider_requests_performed"], 1)
                self.assertTrue(got["central_reservation_retained"])
                self.mock_factory.assert_not_called()

    def test_within_source_revision_returns_retained_summary(self):
        forecast = {
            "forecast_id": "same-id", "symbol": "BTC_USDT_PERP",
            "direction": "long", "confidence": 0.5,
            "published_at_ms": NOW - 1000, "target_time_ms": NOW + 60000,
        }
        self.body = json.dumps({
            "forecasts": [forecast, dict(forecast, direction="short")],
        }).encode()
        try:
            got = self.run_cycle()
        except Exception:
            self.fail("source revision escaped the controlled report boundary")
        self.assertEqual(got["status"], "REVIEW_REQUIRED")
        self.assertEqual(got["stage"], "SOURCE_ACQUISITION")
        self.assertEqual(got["provider_requests_performed"], 1)
        self.assertTrue(got["central_reservation_retained"])
        self.mock_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
