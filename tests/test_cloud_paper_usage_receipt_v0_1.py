"""Cloud-runner evidence-export regression; no real provider or cloud calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.paper.cloud_paper_usage_observation_v0_1 import (
    PaperObservationError, run_observed_slot,
)
import test_paper_v05_prepaid_runtime_v0_1 as paper
import test_prepaid_d1_runtime_v0_1 as fixtures

try:
    from crypto_autopilot.paper.cloud_paper_usage_receipt_v0_1 import write_usage_receipt
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.cloud_paper_usage_receipt_v0_1":
        raise
    write_usage_receipt = None


class PaperUsageReceiptTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(write_usage_receipt, "receipt writer missing")
        self.outer = paper.PaperV05RuntimeTests("test_default_disabled_has_no_requests")
        self.outer.setUp()
        self.addCleanup(self.outer.doCleanups)
        self.f = self.outer.f
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def completed(self):
        _, _, _, opener = self.outer.outer.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            return run_observed_slot(
                self.outer.runtime(), tick_ms=self.f.now, previous_slot=None,
                activation_enabled=True, run_id="github-101-1",
            )

    def test_success_is_bound_to_exact_report_without_exporting_report(self):
        report, observation = self.completed()
        result = write_usage_receipt(self.directory, observation, report=report)
        output = self.directory / "cloud-paper-usage-observation.json"
        body = output.read_bytes()
        data = json.loads(body)
        self.assertEqual(data, observation)
        self.assertEqual(data["status"], "OBSERVED_RETURNED")
        self.assertNotIn("account", data)
        self.assertEqual(result["bytes"], len(body))
        self.assertEqual(len(result["sha256"]), 64)
        self.assertNotIn("synthetic-only-token", body.decode())

    def test_mismatched_report_or_unknown_fields_never_create_file(self):
        report, observation = self.completed()
        for bad_report, bad_observation in (
            ({**report, "slot_id": "999"}, observation),
            (report, {**observation, "secret": "never-write-this"}),
            (report, {**observation, "r2_reserved_class_a": True}),
            (report, {**observation, "provider_confirmed_billing": True}),
        ):
            with self.subTest(bad=bad_observation):
                with self.assertRaises(ValueError):
                    write_usage_receipt(self.directory, bad_observation, report=bad_report)
                self.assertEqual(list(self.directory.iterdir()), [])

    def test_existing_destination_never_overwritten(self):
        report, observation = self.completed()
        path = self.directory / "cloud-paper-usage-observation.json"
        path.write_text("original", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            write_usage_receipt(self.directory, observation, report=report)
        self.assertEqual(path.read_text(encoding="utf-8"), "original")
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), [path.name])

    def test_failed_run_exports_only_redacted_partial_evidence(self):
        db, _, _, _ = self.outer.outer.transport()
        def lost(request, timeout):
            payload = json.loads(request.data)
            db.execute(payload["sql"], tuple(payload["params"])).fetchall()
            db.commit()
            raise OSError("fixture-secret-do-not-persist")
        with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
            network.return_value.open.side_effect = lost
            with self.assertRaises(PaperObservationError) as raised:
                run_observed_slot(self.outer.runtime(), tick_ms=self.f.now,
                    previous_slot=None, activation_enabled=True, run_id="github-101-1")
        write_usage_receipt(self.directory, raised.exception.receipt)
        body = (self.directory / "cloud-paper-usage-observation.json").read_text()
        data = json.loads(body)
        self.assertEqual(data["status"], "REVIEW_REQUIRED")
        self.assertEqual(data["d1_transport_attempts"], 1)
        self.assertIsNone(data["report_id"])
        self.assertNotIn("fixture-secret", body)
