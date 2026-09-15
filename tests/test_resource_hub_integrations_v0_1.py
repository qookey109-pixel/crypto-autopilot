from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from crypto_autopilot.toolkit import list_capabilities_v0_2, validate_statistical_edge


ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS = ROOT / "config" / "resource_hub_integrations_v0_1.json"
TOOLKIT = ROOT / "config" / "qookey_crypto_toolkit_v0_2.json"
WORKFLOW = ROOT / ".github" / "workflows" / "qookey-crypto-toolkit-v0-2-cloud.yml"


class ResourceHubIntegrationsV01Tests(unittest.TestCase):
    def test_statistical_edge_is_deterministic_and_research_only(self) -> None:
        payload = {
            "returns": [0.02, 0.015, 0.01, 0.012, -0.002] * 8,
            "bootstrap_iterations": 500,
            "seed": 7,
            "alpha": 0.05,
            "concentration_top_n": 3,
            "ruin": {
                "initial_equity": 100.0,
                "ruin_fraction": 0.5,
                "horizon_trades": 20,
                "simulations": 200,
                "max_ruin_probability": 0.1,
            },
        }
        first = validate_statistical_edge(payload)
        second = validate_statistical_edge(payload)

        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "qookey-crypto-toolkit-statistical-edge-v0.1")
        self.assertEqual(first["status"], "ANALYZED")
        self.assertEqual(first["mode"], "RESEARCH_ONLY")
        self.assertGreater(first["descriptive"]["mean_return"], 0.0)
        self.assertTrue(first["bootstrap"]["significant_positive_mean"])
        self.assertFalse(first["methodology"]["upstream_runtime_dependency"])
        self.assertFalse(first["methodology"]["automatic_quality_gate_change"])
        self.assertFalse(first["methodology"]["automatic_strategy_mutation"])
        self.assertFalse(first["methodology"]["automatic_model_promotion"])
        self.assertTrue(all(value is False for value in first["authority"].values()))

    def test_statistical_edge_supports_explicit_out_of_sample_evidence(self) -> None:
        result = validate_statistical_edge(
            {
                "returns": [0.01, -0.005, 0.012, 0.004, 0.006, -0.002],
                "train_returns": [0.012, 0.01, 0.008, -0.003],
                "test_returns": [0.004, 0.006, -0.001, 0.003],
                "bootstrap_iterations": 300,
                "seed": 11,
            }
        )
        self.assertIsNotNone(result["out_of_sample"])
        assert result["out_of_sample"] is not None
        self.assertTrue(result["out_of_sample"]["test_positive_mean"])
        self.assertEqual(result["out_of_sample"]["train"]["count"], 4)
        self.assertEqual(result["out_of_sample"]["test"]["count"], 4)

    def test_statistical_edge_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_statistical_edge({"returns": [0.01, math.nan]})
        with self.assertRaisesRegex(ValueError, "below -1.0"):
            validate_statistical_edge({"returns": [0.01, -1.01]})
        with self.assertRaisesRegex(ValueError, "supplied together"):
            validate_statistical_edge(
                {
                    "returns": [0.01, 0.02],
                    "train_returns": [0.01, 0.02],
                    "bootstrap_iterations": 200,
                }
            )
        with self.assertRaisesRegex(ValueError, "between 200 and 20000"):
            validate_statistical_edge(
                {"returns": [0.01, 0.02], "bootstrap_iterations": 10}
            )

    def test_v0_2_capabilities_expose_edge_without_network_or_secrets(self) -> None:
        capabilities = list_capabilities_v0_2()
        tools = {item["name"]: item for item in capabilities["tools"]}
        self.assertIn("validate_statistical_edge", tools)
        edge = tools["validate_statistical_edge"]
        self.assertEqual(edge["category"], "statistical_validation")
        self.assertEqual(edge["side_effects"], "none")
        self.assertFalse(edge["requires_network"])
        self.assertFalse(edge["requires_secrets"])
        self.assertEqual(len(tools), 9)

    def test_resource_hub_registry_keeps_external_integrations_disabled(self) -> None:
        registry = json.loads(INTEGRATIONS.read_text(encoding="utf-8"))
        self.assertEqual(registry["status"], "PREPARED_RESEARCH_ONLY")
        self.assertEqual(
            registry["catalog_source"]["authority_file"], "data/resources.json"
        )
        integrations = {item["id"]: item for item in registry["integrations"]}
        self.assertEqual(
            integrations["anti-gambling-trader-tw"]["integration_status"],
            "IMPLEMENTED_NATIVE_METHODS_ONLY",
        )
        self.assertFalse(integrations["anti-gambling-trader-tw"]["runtime_dependency"])
        self.assertEqual(
            integrations["boundaryml-baml"]["integration_status"],
            "PREPARED_DISABLED",
        )
        self.assertEqual(
            integrations["trailhq-graft"]["integration_status"],
            "PREPARED_DEVELOPER_TOOL_ONLY",
        )
        self.assertEqual(
            integrations["world-monitor"]["integration_status"],
            "PREPARED_EXTERNAL_CONTEXT_DISABLED",
        )
        self.assertEqual(
            integrations["agent-reach"]["integration_status"],
            "PREPARED_RESEARCH_INGESTION_DISABLED",
        )
        self.assertFalse(integrations["agent-reach"]["credentials_or_cookies_in_repository"])
        self.assertTrue(all(value is False for value in registry["global_authority"].values()))

    def test_toolkit_config_and_cloud_workflow_bind_edge_safely(self) -> None:
        toolkit = json.loads(TOOLKIT.read_text(encoding="utf-8"))
        self.assertIn("validate_statistical_edge", toolkit["tools"])
        self.assertEqual(
            toolkit["resource_hub_integrations"]["registry"],
            "config/resource_hub_integrations_v0_1.json",
        )
        self.assertFalse(toolkit["research_guards"]["statistical_edge_automatic_gate_change"])
        self.assertFalse(
            toolkit["research_guards"]["resource_hub_external_network_integrations_enabled"]
        )

        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("          - edge\n", workflow)
        self.assertIn("strategy|risk|backtest|stress|compare|edge|report", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("R2_", workflow)


if __name__ == "__main__":
    unittest.main()
