from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/research-signal-quality-v0-1.yml"
CONFIG = ROOT / "config/research_signal_quality_v0_1.json"


class ResearchSignalQualityWorkflowTests(unittest.TestCase):
    def test_quality_chains_from_successful_main_signal_run_and_keeps_fallback(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "47 2 * * *"', text)
        self.assertIn('workflows: ["Research Signal Layer V0.2"]', text)
        self.assertIn("types: [completed]", text)
        self.assertIn("branches: [main]", text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", text)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", text)
        self.assertIn(
            "github.event.workflow_run.head_repository.full_name == github.repository",
            text,
        )
        self.assertIn("actions: read", text)
        self.assertIn("fetch-depth: 0", text)
        self.assertIn('merge-base", "--is-ancestor"', text)
        self.assertIn("fetch_previous_research_signal_quality.py", text)
        self.assertIn("--previous-report previous-quality/quality.json", text)
        self.assertIn("--expected-run-id", text)
        self.assertIn("cancel-in-progress: true", text)

    def test_config_keeps_quality_read_only_and_defines_exact_dedupe_identity(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            config["quality"]["dedupe_identity"],
            ["run_id", "manifest_sha256", "generated_at_utc"],
        )
        self.assertEqual(
            config["quality"]["same_verified_immutable_run_returns"],
            "NO_CHANGE",
        )
        self.assertEqual(config["quality"]["no_change_max_exact_objects_read"], 1)
        self.assertTrue(config["github_evidence"]["actions_read_only"])
        self.assertTrue(
            config["github_evidence"]["source_run_binding_required_on_workflow_run"]
        )
        self.assertFalse(config["storage"]["r2_list_authorized"])
        self.assertFalse(config["storage"]["r2_write_authorized"])
        self.assertTrue(all(value is False for value in config["authority"].values()))


if __name__ == "__main__":
    unittest.main()
