import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "engineering_workflow_v0_1.json"


class EngineeringWorkflowV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_planning_overlay_has_zero_authority_effect(self) -> None:
        self.assertEqual(self.contract["status"], "ACTIVE_UNIFIED_PLANNING_OVERLAY")
        self.assertEqual(self.contract["authority_effect"], "NONE")
        self.assertFalse(
            self.contract["authority_classifications"]["PLANNING_ONLY"]
            ["external_execution_authorized"]
        )
        self.assertFalse(
            self.contract["authority_classifications"]["WITHIN_EXISTING_AUTHORITY"]
            ["external_execution_authorized_by_ticket"]
        )
        self.assertFalse(
            self.contract["authority_classifications"]["NEW_VERSIONED_AUTHORITY_REQUIRED"]
            ["gated_operation_may_execute"]
        )

    def test_ready_for_agent_cannot_grant_governed_operations(self) -> None:
        blocked = set(self.contract["ready_for_agent"]["does_not_authorize"])
        self.assertEqual(
            blocked,
            {
                "provider_access",
                "r2_list_read_write",
                "holdout_access",
                "source_switch",
                "model_promotion",
                "strategy_or_risk_change",
                "trade_plan",
                "demo_or_live_order",
            },
        )
        self.assertEqual(
            self.contract["ready_for_agent"]["meaning"],
            "IMPLEMENTATION_READY_ONLY",
        )

    def test_frozen_and_secret_boundaries_fail_closed(self) -> None:
        frozen = self.contract["frozen_boundaries"]
        self.assertFalse(frozen["issue_or_pr_may_override"])
        self.assertTrue(frozen["frozen_receipts_and_configs_are_immutable"])
        self.assertFalse(frozen["v0_10_critical_path_change_allowed"])
        self.assertFalse(
            self.contract["secrets"]
            ["allowed_in_issue_pr_comment_artifact_fixture_or_chat"]
        )

    def test_unified_work_item_requires_authority_and_verification_fields(self) -> None:
        task = (ROOT / ".github/ISSUE_TEMPLATE/work-item.yml").read_text()
        pull_request = (ROOT / ".github/pull_request_template.md").read_text()

        for field in (
            "work_type",
            "bounded_outcome",
            "current_evidence",
            "scope_and_slice",
            "acceptance_and_verification",
            "dependencies",
            "decision_frontier",
            "authority_classification",
            "frozen_path_impact",
        ):
            self.assertIn(f"id: {field}", task)

        for work_type in (
            "BUG_TRIAGE",
            "SPECIFICATION",
            "IMPLEMENTATION_TICKET",
            "DECISION_MAP",
        ):
            self.assertIn(f"- {work_type}", task)

        self.assertIn("ready-for-agent", pull_request)
        self.assertIn("V0.10 critical path", pull_request)

    def test_single_issue_form_does_not_auto_apply_authority_labels(self) -> None:
        forms = sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml"))
        self.assertEqual(
            [path.name for path in forms],
            ["config.yml", "work-item.yml"],
        )
        form = (ROOT / ".github/ISSUE_TEMPLATE/work-item.yml").read_text()
        self.assertIn("labels: []", form)
        self.assertNotIn('labels: ["ready-for-agent"]', form)
        self.assertNotIn('labels: ["authority-required"]', form)

    def test_main_is_the_only_long_lived_branch(self) -> None:
        policy = self.contract["branch_policy"]
        self.assertEqual(policy["only_long_lived_branch"], "main")
        self.assertFalse(policy["branch_may_represent_authority_state"])
        self.assertEqual(
            policy["existing_branch_cleanup"],
            "READ_ONLY_AUDIT_THEN_EXPLICIT_APPROVAL",
        )

    def test_agent_instructions_define_the_authority_bridge(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## Planning and issue workflow", agents)
        self.assertIn("implementation-ready", agents)
        self.assertIn("may not execute the gated operation", agents)


if __name__ == "__main__":
    unittest.main()
