from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.toolkit.external_capability_registry_v0_1 import (
    EXPECTED_CAPABILITY_IDS,
    validate_external_capability_registry,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "external_capability_registry_v0_1.json"


class ExternalCapabilityRegistryV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_registry_is_exact_sha_bound_and_candidate_only(self) -> None:
        result = validate_external_capability_registry(self.payload)

        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["capability_count"], 10)
        ids = {row["capability_id"] for row in self.payload["capabilities"]}
        self.assertEqual(ids, EXPECTED_CAPABILITY_IDS)
        self.assertTrue(
            all(
                len(row["commit_sha"]) == 40
                and row["commit_sha"] == row["commit_sha"].lower()
                for row in self.payload["capabilities"]
            )
        )
        self.assertTrue(
            all(
                row["lifecycle_state"] == "CANDIDATE"
                and row["decision"] == "REVIEW_REQUIRED"
                and row["production_eligible"] is False
                and row["adapter_authorized"] is False
                and row["runtime_authorized"] is False
                for row in self.payload["capabilities"]
            )
        )

    def test_project_convergence_indexes_registry_without_runtime_authority(self) -> None:
        convergence = json.loads(
            (ROOT / "config" / "project_convergence_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        registry = convergence["external_capabilities"]
        self.assertEqual(
            registry["registry"],
            "config/external_capability_registry_v0_1.json",
        )
        self.assertEqual(
            registry["documentation"],
            "docs/EXTERNAL_CAPABILITY_REGISTRY_V0_1.md",
        )
        boundaries = convergence["boundaries"]
        self.assertTrue(boundaries["external_capability_registry_added"])
        self.assertFalse(boundaries["external_capability_runtime_authorized"])
        self.assertFalse(boundaries["external_capability_network_authorized"])
        self.assertFalse(boundaries["external_capability_secret_access_authorized"])
        self.assertFalse(boundaries["external_capability_payment_authorized"])
        self.assertFalse(boundaries["external_capability_mutation_authorized"])

    def test_registry_grants_zero_runtime_authority(self) -> None:
        result = validate_external_capability_registry(self.payload)
        authority = result["authority"]
        self.assertTrue(authority["inventory_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "inventory_only"
            )
        )

    def test_write_or_payment_capable_entries_are_high_risk(self) -> None:
        validate_external_capability_registry(self.payload)
        for row in self.payload["capabilities"]:
            risk = row["risk"]
            if risk["upstream_write_capable"] or risk["payment_capable"]:
                self.assertEqual(risk["level"], "HIGH")

    def test_paid_x402_candidate_has_no_wallet_authority(self) -> None:
        agentfeed = next(
            row
            for row in self.payload["capabilities"]
            if row["capability_id"] == "agentfeed"
        )
        self.assertTrue(agentfeed["risk"]["payment_capable"])
        self.assertTrue(agentfeed["requirements"]["paid_runtime"])
        self.assertFalse(self.payload["policy"]["wallet_payment_authorized"])

    def test_high_risk_operator_surfaces_remain_disabled(self) -> None:
        high_risk_ids = {
            row["capability_id"]
            for row in self.payload["capabilities"]
            if row["risk"]["level"] == "HIGH"
        }
        self.assertTrue(
            {
                "agentfeed",
                "telegram_mcp",
                "cloudflare_mcp",
                "github_official_mcp",
                "github_actions_mcp",
            }.issubset(high_risk_ids)
        )
        self.assertFalse(self.payload["policy"]["telegram_write_authorized"])
        self.assertFalse(
            self.payload["policy"]["cloud_infrastructure_mutation_authorized"]
        )
        self.assertFalse(self.payload["policy"]["repository_mutation_authorized"])
        self.assertFalse(self.payload["policy"]["workflow_mutation_authorized"])

    def test_any_runtime_or_strategy_authority_expansion_fails_closed(self) -> None:
        unsafe = deepcopy(self.payload)
        unsafe["policy"]["runtime_execution_authorized"] = True
        with self.assertRaises(ValueError):
            validate_external_capability_registry(unsafe)

        unsafe = deepcopy(self.payload)
        unsafe["policy"]["strategy_router_integration_authorized"] = True
        with self.assertRaises(ValueError):
            validate_external_capability_registry(unsafe)

    def test_candidate_cannot_silently_become_active(self) -> None:
        unsafe = deepcopy(self.payload)
        unsafe["capabilities"][0]["lifecycle_state"] = "ACTIVE"
        with self.assertRaises(ValueError):
            validate_external_capability_registry(unsafe)

    def test_repository_pin_and_license_are_required(self) -> None:
        unsafe = deepcopy(self.payload)
        unsafe["capabilities"][0]["commit_sha"] = "main"
        with self.assertRaises(ValueError):
            validate_external_capability_registry(unsafe)

        unsafe = deepcopy(self.payload)
        unsafe["capabilities"][0]["license_verified"] = False
        with self.assertRaises(ValueError):
            validate_external_capability_registry(unsafe)


if __name__ == "__main__":
    unittest.main()
