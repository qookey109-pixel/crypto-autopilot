from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CurrentOperationsStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = (ROOT / "CURRENT_STATUS.md").read_text(encoding="utf-8")
        self.payload = json.loads(
            (ROOT / "research/status/current-operations-v0-3.json").read_text(
                encoding="utf-8"
            )
        )

    def test_machine_readable_status_matches_current_entrypoint(self) -> None:
        payload = self.payload
        current = self.current

        self.assertEqual(payload["schema"], "qookey-current-operations-v0.3")
        self.assertEqual(payload["updated_date"], "2026-09-22")
        self.assertEqual(payload["repository_authority"], "RESOLVE_MAIN_LIVE_AT_READ_TIME")
        self.assertEqual(payload["mode"], "PAPER_AND_LIVE_PAPER_ONLY")

        basis = payload["evidence_basis"]
        self.assertEqual(
            basis["semantics"],
            "REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION",
        )
        self.assertFalse(basis["is_latest_main_claim"])
        self.assertEqual(basis["source_merge_pr"], 423)
        self.assertEqual(
            basis["parent_main_sha"],
            "b1d75cc54812fc6a355ab5c4535c105c53c26ceb",
        )
        self.assertIn(basis["parent_main_sha"], current)
        self.assertIn("Resolve `main` live at read time", current)
        self.assertIn("not** a latest-main claim", current)

        core100 = payload["core100"]
        self.assertEqual(core100["history_status"], "COMPLETE")
        self.assertEqual(core100["history_complete_shards"], 10)
        self.assertEqual(core100["history_total_shards"], 10)
        self.assertFalse(core100["history_reacquisition_required"])
        self.assertEqual(core100["training_run_id"], 34918219864)
        self.assertEqual(core100["model_quality_gate"]["status"], "REJECT")
        self.assertFalse(core100["model_quality_gate"]["automatic_promotion"])

        replay = core100["threshold_replay"]
        self.assertEqual(replay["run_id"], 34936331199)
        self.assertEqual(replay["workflow_conclusion"], "success")
        self.assertEqual(replay["supported_thresholds"], [])
        self.assertFalse(replay["threshold_change_supported"])
        self.assertFalse(replay["configured_threshold_changed"])

        fingerprint = core100["dataset_fingerprint"]
        self.assertIn(fingerprint, current)
        self.assertIn(str(core100["training_run_id"]), current)
        self.assertIn(str(replay["run_id"]), current)
        self.assertIn("History COMPLETE", current)
        self.assertIn("Model Quality REJECT", current)
        self.assertNotIn("Training SKIPPED", current)
        self.assertNotIn("History 8/10", current)

    def test_status_does_not_claim_evidence_basis_is_latest_main(self) -> None:
        basis = self.payload["evidence_basis"]
        control = self.payload["control_plane"]
        self.assertFalse(basis["is_latest_main_claim"])
        self.assertFalse(control["self_referential_latest_main_sha_allowed"])
        self.assertNotIn("Reviewed `main`:", self.current)
        self.assertNotIn("Merge-after CI passed on current `main`", self.current)

    def test_pionex_v0_2_materialization_completion_is_exact_and_bounded(self) -> None:
        pionex = self.payload["pionex_validation"]
        authority = pionex["authority"]

        self.assertEqual(
            pionex["workflow"],
            ".github/workflows/pionex-validation-materialization-v0-2.yml",
        )
        self.assertEqual(pionex["dispatch_mode"], "MANUAL_ONLY")
        self.assertEqual(pionex["repository_materialization_status"], "COMPLETE_PASS")
        self.assertEqual(pionex["materialization_run_id"], 35054729471)
        self.assertEqual(pionex["materialization_run_attempt"], 1)
        self.assertEqual(pionex["materialization_run_outcome"], "PASS")
        self.assertEqual(
            pionex["report_stage"], "PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_2"
        )
        self.assertEqual(pionex["artifact_id"], 10430054351)
        self.assertEqual(pionex["selected_market_count"], 197)
        self.assertEqual(pionex["partition_count"], 682)
        self.assertEqual(pionex["provider_requests"], 1534)
        self.assertTrue(pionex["r2_latest_pointer_written_last"])
        self.assertFalse(pionex["complete_197_market_multiyear_history_claimed"])
        self.assertFalse(pionex["core100_pionex_training_performed"])
        self.assertEqual(
            pionex["completion_evidence"],
            "research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json",
        )
        self.assertTrue(authority["public_pionex_kline_reads"])
        self.assertTrue(authority["r2_validation_dataset_writes"])
        self.assertFalse(authority["private_api"])
        self.assertFalse(authority["account_data"])
        self.assertFalse(authority["replacement_holdout_access"])
        self.assertFalse(authority["training"])
        self.assertFalse(authority["source_switch"])
        self.assertFalse(authority["automatic_model_promotion"])
        self.assertFalse(authority["formal_trade_plan"])
        self.assertFalse(authority["real_money_orders"])
        self.assertFalse(authority["live_trading"])

    def test_agents_read_current_status_before_dated_status(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        current_pos = agents.find("`CURRENT_STATUS.md`")
        project_pos = agents.find("`PROJECT_STATUS.md`")
        self.assertGreaterEqual(current_pos, 0)
        self.assertGreater(project_pos, current_pos)

    def test_closed_authority_boundaries_remain_closed(self) -> None:
        gates = self.payload["gates"]
        self.assertEqual(gates["strategy_validation"], "CLOSED")
        self.assertEqual(gates["holdout"], "FROZEN_UNOPENED")
        self.assertEqual(gates["automatic_model_promotion"], "CLOSED")
        self.assertEqual(gates["formal_trade_plan"], "CLOSED")
        self.assertEqual(gates["real_money_orders"], "CLOSED")
        self.assertEqual(
            gates["live_paper_simulation"],
            "AUTHORIZED_PUBLIC_MARKET_PAPER_ONLY",
        )
        self.assertEqual(gates["live_trading"], "CLOSED")
        self.assertFalse(gates["source_switch_authorized"])

        live_paper = self.payload["live_paper"]
        self.assertTrue(live_paper["public_live_market_data"])
        self.assertTrue(live_paper["live_paper_simulation"])
        self.assertTrue(live_paper["paper_state_persistence"])
        self.assertFalse(live_paper["private_exchange_api"])
        self.assertFalse(live_paper["replacement_holdout_access"])
        self.assertFalse(live_paper["real_money_orders"])
        self.assertFalse(live_paper["live_real_trading"])

    def test_reliability_convergence_is_current_and_authority_stays_bounded(self) -> None:
        control = self.payload["control_plane"]
        live_paper = self.payload["live_paper"]

        self.assertEqual(
            control["research_signal_quality_state"],
            "UPSTREAM_COMPLETION_CHAINED_WITH_EXACT_IMMUTABLE_RUN_DEDUP_AND_DAILY_FALLBACK",
        )
        self.assertEqual(
            control["dashboard_browser_validation_state"],
            "PLAYWRIGHT_CHROMIUM_DESKTOP_MOBILE_PR_BUILD_PLUS_POST_DEPLOY_PRODUCTION_CHECK",
        )
        self.assertEqual(
            control["live_paper_slot_claim_state"],
            "ACTIVE_MANUAL_COORDINATOR_FAIL_CLOSED_ATOMIC_CREATE_IF_ABSENT",
        )
        self.assertEqual(
            live_paper["coordinator_contract"],
            "config/live_paper_run_coordinator_v0_2.json",
        )
        self.assertEqual(
            live_paper["run_slot_claim_contract"],
            "config/live_paper_run_claim_v0_1.json",
        )
        self.assertEqual(
            live_paper["coordinator_dispatch_mode"],
            "MANUAL_WORKFLOW_DISPATCH_ONLY",
        )
        self.assertTrue(live_paper["run_slot_claim_required"])
        self.assertTrue(live_paper["atomic_create_if_absent_required"])
        self.assertFalse(live_paper["claim_expiry_authorized"])
        self.assertFalse(live_paper["claim_takeover_authorized"])
        self.assertFalse(live_paper["claim_conflict_auto_retry_authorized"])
        self.assertFalse(live_paper["private_exchange_api"])
        self.assertFalse(live_paper["replacement_holdout_access"])
        self.assertFalse(live_paper["real_money_orders"])
        self.assertFalse(live_paper["live_real_trading"])
        self.assertIn("PR #421", self.current)
        self.assertIn("PR #422", self.current)
        self.assertIn("PR #423", self.current)
        self.assertIn('IfNoneMatch="*"', self.current)
        self.assertNotIn(
            "This prepared change becomes current authority only if its pull request is explicitly merged",
            self.current,
        )

    def test_control_plane_contract_requires_current_overlay(self) -> None:
        control = self.payload["control_plane"]
        self.assertEqual(
            control["dashboard_projection_policy"],
            "HISTORICAL_AUTHORITY_OVERLAY_THEN_CURRENT_OPERATIONS_OVERLAY",
        )
        self.assertEqual(
            control["homepage_projection_policy"],
            "CURRENT_OPERATIONS_MUST_OVERRIDE_DATED_SIMULATION_READINESS_FOR_PRESENT_TENSE_STATE",
        )

    def test_technical_debt_register_exists(self) -> None:
        register = (
            ROOT / "docs/TECH_DEBT_REGISTER_2026_09_16.md"
        ).read_text(encoding="utf-8")
        self.assertIn("TD-001", register)
        self.assertIn("TD-002", register)
        self.assertIn("TD-009", register)
        self.assertIn("control-plane", register)


if __name__ == "__main__":
    unittest.main()
