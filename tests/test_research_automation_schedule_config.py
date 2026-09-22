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

    def test_health_inventory_count_is_derived_not_hard_coded(self) -> None:
        health = _json("config/research_automation_health_v0_2.json")
        coverage = health["coverage"]
        self.assertEqual(
            coverage["policy"],
            "EXACT_REPOSITORY_SCHEDULE_INVENTORY",
        )
        self.assertTrue(coverage["require_every_repository_cron"])
        self.assertTrue(coverage["derive_expected_count_from_workflows_inventory"])
        self.assertNotIn("expected_scheduled_workflow_count", coverage)

        workflow = (
            ROOT / ".github/workflows/research-automation-health-v0-2.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('inventory_count = len(config["workflows"])', workflow)
        self.assertIn(
            'coverage["scheduled_workflow_count"] == inventory_count',
            workflow,
        )
        self.assertIn(
            'coverage["monitored_workflow_count"] == inventory_count',
            workflow,
        )
        self.assertNotIn('coverage["scheduled_workflow_count"] == 7', workflow)

    def test_authority_receipts_preserve_history_and_bind_prepared_revision(self) -> None:
        historical = _json(
            "research/receipts/2026-08-24-research-automation-health-v0-1-authority.json"
        )
        historical_hashes = {
            ".github/workflows/research-automation-health-v0-1.yml":
                "64da84b0966b74de3939605873dc0e4edd2147a7eb276ad6e5afe2d23bd72b68",
            "config/research_signal_quality_v0_1.json":
                "b99938e41d6fb95a37e9296155f5f669b6b5e939d5e8fd8d04bb8a5675228457",
            ".github/workflows/research-signal-quality-v0-1.yml":
                "12378d8345f930486a77e598d5547c8eea297e61f21a3cbfb4762ff1284ac49b",
        }
        for row in historical["bound_files"]:
            path = row["path"]
            if path in historical_hashes:
                self.assertEqual(row["sha256"], historical_hashes[path])
                continue
            payload = (ROOT / path).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])

        prepared = _json(
            "research/receipts/2026-09-22-research-signal-quality-v0-2-prepared.json"
        )
        self.assertEqual(
            prepared["status"],
            "PREPARED_AWAITING_EXPLICIT_MERGE_AUTHORIZATION",
        )
        self.assertFalse(prepared["merge_authority_granted_by_this_receipt"])
        for row in prepared["bound_files"]:
            payload = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])
        self.assertTrue(
            all(value is False for value in prepared["explicitly_not_authorized"].values())
        )

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
