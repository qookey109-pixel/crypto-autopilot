from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pionex-public-paper-training-v0-1.yml"


class PaperTrainingWorkflowTests(unittest.TestCase):
    def test_workflow_is_public_paper_only_and_demo_manual(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("  schedule:", text)
        self.assertIn("  workflow_dispatch:", text)
        self.assertIn("scripts/build_strategy_projection.py", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("paper-training.json", text)
        self.assertNotIn("PIONEX_API_KEY", text)
        self.assertNotIn("PIONEX_API_SECRET", text)
        self.assertNotIn("/api/v1/trade", text)
        self.assertNotIn("place_order", text.lower())

    def test_holdout_boundary_skips_before_any_provider_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "paper-training.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_pionex_paper_training.py"),
                    "--config",
                    str(ROOT / "config" / "paper_training_v0_1.json"),
                    "--output",
                    str(output),
                    "--run-id",
                    "holdout-unit-test",
                    "--now-ms",
                    "1787788800000",
                ],
                check=True,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "SKIPPED")
        self.assertEqual(report["authority"]["providerRequestsPerformed"], 0)
        self.assertFalse(report["authority"]["holdoutAccessed"])


if __name__ == "__main__":
    unittest.main()
