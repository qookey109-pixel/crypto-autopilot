"""CI evidence should join real adapters with synthetic-only services."""
import json
import tempfile
import unittest
from pathlib import Path

try:
    from scripts.cloud_paper_usage_synthetic_evidence_v0_1 import produce_evidence
except ModuleNotFoundError as exc:
    if exc.name != "scripts.cloud_paper_usage_synthetic_evidence_v0_1":
        raise
    produce_evidence = None


class SyntheticUsageEvidenceTests(unittest.TestCase):
    def test_complete_and_ambiguous_cases_emit_distinct_redacted_receipts(self):
        self.assertIsNotNone(produce_evidence, "synthetic evidence producer missing")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence"
            manifest = produce_evidence(output, run_id="github-101-1", source_sha="a" * 40)
            self.assertEqual(manifest["evidence_type"], "SYNTHETIC_CI_ONLY")
            self.assertEqual(manifest["source_sha_unattested"], "a" * 40)
            self.assertFalse(manifest["production_data_service_access"])
            success = json.loads((output / "completed" / "cloud-paper-usage-observation.json").read_text())
            failure = json.loads((output / "ambiguous" / "cloud-paper-usage-observation.json").read_text())
            self.assertEqual(success["status"], "OBSERVED_RETURNED")
            self.assertTrue(success["report_id"])
            self.assertEqual(failure["status"], "REVIEW_REQUIRED")
            self.assertIsNone(failure["report_id"])
            self.assertEqual(failure["d1_transport_attempts"], 1)
            for scenario, value in (("completed", success), ("ambiguous", failure)):
                self.assertEqual(manifest["scenarios"][scenario]["receipt_sha256"],
                                 __import__("hashlib").sha256(
                                     (output / scenario / "cloud-paper-usage-observation.json").read_bytes()
                                 ).hexdigest())
                self.assertNotIn("synthetic-only-token", json.dumps(value))
                self.assertNotIn("fixture-secret", json.dumps(value))

    def test_rejects_invalid_identity_before_creating_output(self):
        self.assertIsNotNone(produce_evidence, "synthetic evidence producer missing")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence"
            with self.assertRaises(ValueError):
                produce_evidence(output, run_id="not-a-run", source_sha="a" * 40)
            self.assertFalse(output.exists())


    def test_artifact_readback_requires_identical_complete_file_set(self):
        import shutil
        from scripts.cloud_paper_usage_synthetic_evidence_v0_1 import verify_downloaded_evidence

        with tempfile.TemporaryDirectory() as temp:
            expected = Path(temp) / "expected"
            downloaded = Path(temp) / "downloaded"
            produce_evidence(expected, run_id="github-101-1", source_sha="a" * 40)
            shutil.copytree(expected, downloaded)
            self.assertEqual(verify_downloaded_evidence(expected, downloaded)["status"],
                             "SYNTHETIC_ARTIFACT_READBACK_VERIFIED")
            receipt = downloaded / "completed" / "cloud-paper-usage-observation.json"
            receipt.write_text("changed")
            with self.assertRaisesRegex(ValueError, "READBACK_MISMATCH"):
                verify_downloaded_evidence(expected, downloaded)
            receipt.unlink()
            with self.assertRaisesRegex(ValueError, "FILE_SET_MISMATCH"):
                verify_downloaded_evidence(expected, downloaded)
