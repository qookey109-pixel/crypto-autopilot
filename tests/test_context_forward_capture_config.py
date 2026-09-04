from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture import (
    validate_context_forward_capture_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "context_forward_capture_v0_1.json"
SOURCE_PATH = ROOT / "config" / "context_source_lineage_v0_1.json"
CLOUD_POLICY_PATH = ROOT / "config" / "cloud_free_tier_policy_v0_1.json"
EXECUTION_CONFIG_PATH = ROOT / "config" / "context_forward_capture_execution_v0_1.json"
EXECUTION_WORKFLOW_NAME = "context-forward-capture-execution-v0-1.yml"


class ContextForwardCaptureConfigTests(unittest.TestCase):
    def test_config_is_bound_to_exact_source_lineage_bytes(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        source_bytes = SOURCE_PATH.read_bytes()

        validate_context_forward_capture_config(config, source_lineage_bytes=source_bytes)
        self.assertEqual(
            config["source_lineage"]["sha256"], hashlib.sha256(source_bytes).hexdigest()
        )
        self.assertEqual(config["status"], "PREPARED_NOT_ACTIVE")

    def test_zero_cost_projection_stays_far_below_documented_free_allowance(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cloud = json.loads(CLOUD_POLICY_PATH.read_text(encoding="utf-8"))

        self.assertEqual(cloud["monthly_budget_usd"], 0)
        self.assertFalse(cloud["billing_policy"]["paid_fallback_authorized"])
        self.assertEqual(config["zero_cost_policy"]["monthly_budget_usd"], 0)
        self.assertFalse(config["zero_cost_policy"]["paid_fallback_allowed"])
        self.assertLessEqual(
            config["capacity_projection"]["projected_requests_per_30_day_month"],
            config["zero_cost_policy"]["documented_provider_request_limit_per_month"],
        )
        self.assertTrue(config["capacity_projection"]["projection_is_not_execution_authority"])

    def test_every_runtime_and_trading_authority_remains_false(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        authority = config["authority"]

        self.assertTrue(authority["research_only"])
        for key, value in authority.items():
            if key != "research_only":
                with self.subTest(key=key):
                    self.assertFalse(value)

        self.assertIsNone(config["storage"]["production_r2_namespace"])
        self.assertFalse(config["transport_preparation"]["provider_request_entrypoint_enabled"])
        self.assertFalse(config["transport_preparation"]["default_network_transport_implemented"])

    def test_prepared_capture_has_no_self_authorized_workflow(self) -> None:
        """A workflow may exist only through the separate versioned execution authority."""

        prepared = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertFalse(prepared["authority"]["provider_fetch_authorized"])
        self.assertFalse(prepared["authority"]["workflow_schedule_authorized"])
        self.assertFalse(prepared["transport_preparation"]["provider_request_entrypoint_enabled"])

        workflow_root = ROOT / ".github" / "workflows"
        matching: list[Path] = []
        for path in workflow_root.glob("*.yml"):
            text = path.read_text(encoding="utf-8").lower()
            if "context_forward_capture" in text or "context-forward-capture" in text:
                matching.append(path)

        self.assertEqual([path.name for path in matching], [EXECUTION_WORKFLOW_NAME])
        execution = json.loads(EXECUTION_CONFIG_PATH.read_text(encoding="utf-8"))
        workflow = matching[0].read_text(encoding="utf-8")
        self.assertEqual(execution["execution"]["mode"], "MANUAL_ONE_SHOT")
        self.assertTrue(execution["execution"]["workflow_dispatch_authorized"])
        self.assertFalse(execution["execution"]["workflow_schedule_authorized"])
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertIn("context_forward_capture_execution_v0_1.json", workflow)


if __name__ == "__main__":
    unittest.main()
