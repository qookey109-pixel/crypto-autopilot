from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.preflight_cloud_paper_loop_v0_1 import ROOT, build_report


class CloudPaperNonAccessPreflightTests(unittest.TestCase):
    def _inputs(self) -> tuple[dict, dict, dict, dict]:
        return (
            json.loads((ROOT / "config/cloud_paper_loop_v0_1.json").read_text()),
            json.loads((ROOT / "research/status/cloud-paper-delivery-v0-1.json").read_text()),
            json.loads((ROOT / "config/cloud_paper_strategy_registry_v0_1.json").read_text()),
            json.loads(
                (
                    ROOT
                    / "research/status/cloud-paper-r2-writer-inventory-v0-1.json"
                ).read_text()
            ),
        )

    def test_current_preflight_is_disabled_and_has_zero_external_access(self) -> None:
        report = build_report(*self._inputs())
        self.assertEqual(report["status"], "DISABLED")
        self.assertEqual(report["strategy_outcome"], "NOT_EVALUATED")
        self.assertEqual(report["external_access"]["provider_requests_performed"], 0)
        self.assertIs(report["external_access"]["r2_access_performed"], False)
        self.assertIs(report["external_access"]["d1_access_performed"], False)
        self.assertIn("R2_USAGE_EVIDENCE_MISSING", report["reason_codes"])
        self.assertIn("D1_LEDGER_NOT_READY", report["reason_codes"])

    def test_nonaccess_preflight_refuses_enabled_activation(self) -> None:
        values = self._inputs()
        values[0]["activation"]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "activation to remain disabled"):
            build_report(*values)

    def test_empty_strategy_registry_is_reported_without_inventing_no_trade(self) -> None:
        report = build_report(*self._inputs())
        self.assertIn("STRATEGY_REGISTRY_EMPTY", report["reason_codes"])
        self.assertEqual(report["strategy_outcome"], "NOT_EVALUATED")
        self.assertIs(report["authority"]["model_promotion"], False)


if __name__ == "__main__":
    unittest.main()
