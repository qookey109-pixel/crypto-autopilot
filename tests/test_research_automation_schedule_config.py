from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ResearchAutomationScheduleConfigTests(unittest.TestCase):
    def test_active_crons_match_versioned_configs(self) -> None:
        health = _json("config/research_automation_health_v0_2.json")
        quality = _json("config/research_signal_quality_v0_1.json")
        health_workflow = (
            ROOT / ".github/workflows/research-automation-health-v0-2.yml"
        ).read_text()
        quality_workflow = (
            ROOT / ".github/workflows/research-signal-quality-v0-1.yml"
        ).read_text()
        self.assertIn(f'cron: "{health["schedule"]["cron_utc"]}"', health_workflow)
        self.assertIn(f'cron: "{quality["schedule"]["cron_utc"]}"', quality_workflow)
        self.assertIn("actions: read", health_workflow)
        self.assertIn("schedule:", health_workflow)
        self.assertIn("schedule:", quality_workflow)
        retired = (
            ROOT / ".github/workflows/research-automation-health-v0-1.yml"
        ).read_text()
        self.assertNotIn("  schedule:", retired)
        self.assertIn("  workflow_dispatch:", retired)

    def test_authority_receipt_binds_exact_config_and_workflow_bytes(self) -> None:
        receipt = _json(
            "research/receipts/2026-08-24-research-automation-health-v0-1-authority.json"
        )
        for row in receipt["bound_files"]:
            if row["path"] == ".github/workflows/research-automation-health-v0-1.yml":
                self.assertEqual(
                    row["sha256"],
                    "64da84b0966b74de3939605873dc0e4edd2147a7eb276ad6e5afe2d23bd72b68",
                )
                continue
            payload = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])

    def test_post_window_schedule_is_prepared_without_execution_authority(self) -> None:
        config = _json("config/post_window_research_successor_schedule_v0_1.json")
        self.assertEqual(config["status"], "PREPARED_NOT_ACTIVE")
        self.assertFalse(config["activation"]["automatic_activation"])
        self.assertTrue(
            config["activation"]["separate_versioned_execution_authority_required"]
        )
        self.assertTrue(
            all(item["state"] == "PROPOSED_ONLY" for item in config["proposed_schedule"])
        )
        self.assertTrue(all(value is False for value in config["current_authority"].values()))


if __name__ == "__main__":
    unittest.main()
