from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "config" / "project_convergence_v0_1.json"
RETIREMENT = ROOT / "config" / "post_cutoff_schedule_retirement_v0_1.json"
RETIREMENT_RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-08-29-post-cutoff-schedule-retirement-v0-1-effective-on-merge.json"
)
WORKFLOWS = ROOT / ".github" / "workflows"


class ProjectConvergenceV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = json.loads(INDEX.read_text(encoding="utf-8"))

    def test_every_workflow_has_exactly_one_current_classification(self) -> None:
        actual = {path.name for path in WORKFLOWS.glob("*.yml")}
        groups = self.index["workflow_groups"]
        classified = [name for group in groups.values() for name in group]
        self.assertEqual(len(classified), len(set(classified)), "duplicate workflow classification")
        self.assertEqual(set(classified), actual)

    def test_every_remaining_cron_is_declared_exactly(self) -> None:
        declared: dict[str, list[str]] = {}
        for group in self.index["scheduled_workflows"].values():
            for item in group:
                declared[item["workflow"]] = item["cron_utc"]

        actual: dict[str, list[str]] = {}
        for path in sorted(WORKFLOWS.glob("*.yml")):
            crons = []
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("- cron: "):
                    crons.append(stripped.removeprefix("- cron: ").strip('"'))
            if crons:
                actual[path.name] = crons
        self.assertEqual(actual, declared)

    def test_expired_crons_are_retired_but_manual_fail_closed_entry_remains(self) -> None:
        retirement = json.loads(RETIREMENT.read_text(encoding="utf-8"))
        retired = {item["workflow"] for item in retirement["retired_schedule_triggers"]}
        self.assertEqual(retired, set(self.index["post_cutoff_manual_regressions"]))
        for name in retired:
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            self.assertNotIn("  schedule:", text)
            self.assertIn("  workflow_dispatch:", text)
        self.assertFalse(retirement["retained_behavior"]["automatic_resume"])
        self.assertTrue(all(value is False for value in retirement["authority"].values()))

    def test_retirement_receipt_binds_exact_config(self) -> None:
        receipt = json.loads(RETIREMENT_RECEIPT.read_text(encoding="utf-8"))
        digest = hashlib.sha256(RETIREMENT.read_bytes()).hexdigest()
        self.assertEqual(receipt["config"]["sha256"], digest)
        self.assertEqual(receipt["retired_schedule_count"], 3)
        self.assertEqual(receipt["authority"]["provider_requests_performed"], 0)
        for key, value in receipt["authority"].items():
            if key != "provider_requests_performed":
                self.assertFalse(value, key)

    def test_current_web_tree_has_one_large_visual_and_typed_assets(self) -> None:
        website = self.index["website"]
        for relative in (
            website["entry"],
            website["script"],
            *website["styles"],
            *website["active_large_assets"],
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        current_jpgs = sorted((ROOT / "web" / "assets").rglob("*.jpg"))
        self.assertEqual(
            current_jpgs,
            [ROOT / "web" / "assets" / "images" / "cloud-garden-v4.jpg"],
        )

    def test_convergence_index_cannot_claim_runtime_or_trading_authority(self) -> None:
        self.assertIs(self.index["authority"], False)
        boundaries = self.index["boundaries"]
        self.assertFalse(boundaries["v0_10_production_critical_path_changed"])
        self.assertFalse(boundaries["sstate_core_changed"])
        self.assertFalse(boundaries["strategy_parameters_changed"])
        self.assertTrue(boundaries["provider_or_r2_authority_added"])
        self.assertTrue(boundaries["provider_or_r2_scope_replaced_before_execution"])
        self.assertFalse(boundaries["replacement_holdout_access_authorized"])
        self.assertFalse(boundaries["paper_successor_automatic_activation_authorized"])
        self.assertFalse(boundaries["live_trading_authorized"])

    def test_current_data_and_paper_index_is_bounded(self) -> None:
        current = self.index["current_data_and_paper"]
        self.assertEqual(
            current["crypto_core_100"],
            "config/binance_usdm_detailed_history_v0_1_2.json",
        )
        self.assertEqual(
            current["pionex_alternative_assets_state"],
            "CATALOG_AUTHORIZED_AFTER_V0_10_WINDOW_HISTORY_WAITING_HOLDOUT_AUTHORITY",
        )
        self.assertEqual(
            current["paper_successor_state"],
            "PREPARED_WAITING_FOR_HOLDOUT_AUTHORITY",
        )
        for key in (
            "crypto_core_100",
            "crypto_core_100_authority",
            "pionex_alternative_assets_catalog",
            "pionex_alternative_assets_authority",
            "paper_successor",
        ):
            self.assertTrue((ROOT / current[key]).is_file(), current[key])


if __name__ == "__main__":
    unittest.main()
