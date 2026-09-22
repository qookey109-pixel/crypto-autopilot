from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "research" / "status" / "type-debt-baseline-v0-1.json"


class TypeDebtBaselineV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_evidence_and_policy_are_exact(self) -> None:
        payload = self.payload
        self.assertEqual(payload["schema"], "qookey-type-debt-baseline-v0.1")
        self.assertEqual(payload["snapshot_date"], "2026-09-22")
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 427)
        self.assertEqual(payload["evidence_basis"]["ci_run_id"], 35685558516)
        self.assertEqual(payload["evidence_basis"]["artifact_id"], 10676955738)
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])
        self.assertFalse(payload["remediation_policy"]["blocking_gate"])
        self.assertFalse(payload["remediation_policy"]["threshold_enforced"])
        self.assertFalse(payload["remediation_policy"]["blanket_any_authorized"])
        self.assertFalse(payload["remediation_policy"]["blanket_type_ignore_authorized"])
        self.assertFalse(payload["remediation_policy"]["behavior_change_authorized"])

    def test_error_counts_match_measured_artifact(self) -> None:
        result = self.payload["result"]
        self.assertEqual(result["diagnostic_count"], 465)
        self.assertEqual(result["error_count"], 261)
        self.assertEqual(result["note_count"], 204)
        self.assertEqual(result["files_with_errors"], 49)
        self.assertFalse(result["baseline_clean"])
        self.assertEqual(sum(self.payload["error_codes"].values()), 261)

    def test_dominant_error_families_are_explicit(self) -> None:
        concentration = self.payload["concentration"]
        self.assertEqual(
            concentration["top_three_codes"],
            ["arg-type", "call-overload", "attr-defined"],
        )
        self.assertEqual(concentration["top_three_error_count"], 215)
        self.assertAlmostEqual(concentration["top_three_fraction"], 215 / 261, places=9)

    def test_execution_sensitive_paper_paths_are_deferred(self) -> None:
        deferred = set(self.payload["remediation_policy"]["deferred_sensitive_paths"])
        self.assertIn("src/crypto_autopilot/paper/live_v0_1.py", deferred)
        self.assertIn("src/crypto_autopilot/paper/run_coordinator_v0_1.py", deferred)
        self.assertIn("src/crypto_autopilot/paper/run_recovery_v0_1.py", deferred)

    def test_human_baseline_exists(self) -> None:
        text = (ROOT / "docs" / "TYPE_DEBT_BASELINE_2026_09_22.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("261 errors", text)
        self.assertIn("215 / 261 errors (82.38%)", text)
        self.assertIn("blanket `Any`", text)
        self.assertIn("informational", text)


if __name__ == "__main__":
    unittest.main()
