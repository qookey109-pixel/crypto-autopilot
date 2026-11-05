"""Post-run observation through the prepared Paper composition, no real network."""
import json
import unittest
from unittest.mock import patch

import test_paper_v05_prepaid_runtime_v0_1 as paper
import test_prepaid_d1_runtime_v0_1 as fixtures

try:
    from crypto_autopilot.paper.cloud_paper_usage_observation_v0_1 import (
        PaperObservationError, run_observed_slot,
    )
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.cloud_paper_usage_observation_v0_1":
        raise
    PaperObservationError = run_observed_slot = None


class PaperUsageObservationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(run_observed_slot, "observation entrypoint missing")
        self.outer = paper.PaperV05RuntimeTests("test_default_disabled_has_no_requests")
        self.outer.setUp()
        self.addCleanup(self.outer.doCleanups)
        self.f = self.outer.f

    def test_completed_run_records_sdk_attempts_after_readback_and_settlement(self):
        _, _, statements, opener = self.outer.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            runtime = self.outer.runtime()
            result, receipt = run_observed_slot(
                runtime, tick_ms=self.f.now, previous_slot=None,
                activation_enabled=True, run_id="github-101-1",
            )
        self.assertEqual(result["state"], "NO_TRADE")
        self.assertEqual(receipt["status"], "OBSERVED_RETURNED")
        self.assertEqual(receipt["report_id"], __import__(
            "crypto_autopilot.paper.cloud_loop_v0_1", fromlist=["digest"]
        ).digest(result))
        calls = self.f.sdk.calls
        for operation in ("PUT", "GET", "LIST"):
            self.assertEqual(receipt["r2_sdk_attempts"][operation],
                             sum(call["operation"] == operation for call in calls))
        self.assertEqual(receipt["d1_transport_attempts"], len(statements))
        self.assertEqual(receipt["d1_ticket_debits"], 4)
        self.assertEqual(receipt["provider_reserved_attempts"], 0)
        self.assertFalse(receipt["provider_confirmed_billing"])
        self.assertEqual(result["operation_counts"]["status"], "PARTIAL")

    def test_failure_receipt_is_redacted_and_keeps_attempts(self):
        db, _, _, _ = self.outer.outer.transport()
        def lost(request, timeout):
            payload = json.loads(request.data)
            db.execute(payload["sql"], tuple(payload["params"])).fetchall()
            db.commit()
            raise OSError("fixture-credential-must-not-leak")
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
            network.return_value.open.side_effect = lost
            runtime = self.outer.runtime()
            with self.assertRaises(PaperObservationError) as raised:
                run_observed_slot(runtime, tick_ms=self.f.now, previous_slot=None,
                                  activation_enabled=True, run_id="github-101-1")
        receipt = raised.exception.receipt
        self.assertEqual(receipt["status"], "REVIEW_REQUIRED")
        self.assertEqual(receipt["d1_transport_attempts"], 1)
        self.assertEqual(receipt["d1_ticket_debits"], 2)
        self.assertEqual(receipt["r2_sdk_attempts"], {"PUT": 0, "GET": 0, "LIST": 0})
        self.assertNotIn("fixture-credential", json.dumps(receipt))
        self.assertIsNone(receipt["report_id"])

    def test_disabled_or_dirty_runtime_stops_without_external_access(self):
        runtime = self.outer.runtime()
        result, receipt = run_observed_slot(
            runtime, tick_ms=self.f.now, previous_slot=None, activation_enabled=False,
            run_id="github-101-1",
        )
        self.assertEqual(result["state"], "DISABLED")
        self.assertEqual(receipt["status"], "DISABLED")
        self.assertEqual(self.f.sdk.calls, [])
        runtime.budget_guard._class_a_run = 1
        with self.assertRaises(ValueError):
            run_observed_slot(runtime, tick_ms=self.f.now, previous_slot=None,
                              activation_enabled=True, run_id="github-101-1")
        self.assertEqual(self.f.sdk.calls, [])


    def test_r2_transport_failure_is_counted_once_without_secret_leak(self):
        _, _, _, opener = self.outer.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            runtime = self.outer.runtime()
            with patch.object(self.f.sdk, "put_object",
                              side_effect=OSError("fixture-secret-r2-error")) as write:
                with self.assertRaises(PaperObservationError) as raised:
                    run_observed_slot(runtime, tick_ms=self.f.now, previous_slot=None,
                                      activation_enabled=True, run_id="github-101-1")
        receipt = raised.exception.receipt
        self.assertEqual(receipt["status"], "REVIEW_REQUIRED")
        self.assertEqual(receipt["r2_sdk_attempts"]["PUT"], 1)
        self.assertEqual(write.call_count, 1)
        self.assertGreaterEqual(receipt["r2_reserved_class_a"], 1)
        self.assertIsNone(receipt["report_id"])
        self.assertNotIn("fixture-secret", json.dumps(receipt))
