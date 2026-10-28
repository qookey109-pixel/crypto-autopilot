from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("delivery_replay", ROOT / "scripts/build_delivery_overview.py")
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class ReplayEvidencePanelTests(unittest.TestCase):
    def test_verified_single_archive_has_bounded_research_summary(self) -> None:
        receipt = delivery.read_json(delivery.SHADOW_REPLAY_RECEIPT)
        panel = delivery.shadow_replay_evidence_panel(receipt)
        self.assertIn("5 市場", panel)
        self.assertIn("20 次抽樣", panel)
        self.assertIn("2026-10-25T04:43:38.396000Z", panel)
        self.assertIn("40618806942", panel)
        self.assertIn("歷史資料版本：UNKNOWN", panel)
        self.assertIn("正式 PAPER", panel)

    def test_missing_or_changed_receipt_fails_closed(self) -> None:
        original = delivery.read_json(delivery.SHADOW_REPLAY_RECEIPT)
        changes = (
            ("source", "original_zip_sha256", "0" * 64),
            ("source", "github_metadata_and_zip_verified_by_hosted_audit", False),
            ("result", "sampled_prefix_future_mutation_checks", 21),
            ("result", "historical_entry_cutoff_proven", True),
            ("result", "formal_paper_executed", True),
            ("authority", "paper_submission", True),
            ("evidence_basis", "whole_pr_ci_passed", True),
        )
        for section, key, value in changes:
            changed = copy.deepcopy(original)
            changed[section][key] = value
            with self.subTest(section=section, key=key):
                panel = delivery.shadow_replay_evidence_panel(changed)
                self.assertIn("UNKNOWN", panel)
                self.assertNotIn("20 次抽樣", panel)
        self.assertIn("UNKNOWN", delivery.shadow_replay_evidence_panel(None))

    def test_market_panel_includes_only_validated_replay_projection(self) -> None:
        current = delivery.read_json(delivery.CURRENT_OPERATIONS)
        panel = delivery.market_decision_panel(current)
        self.assertIn("20 次抽樣", panel)
        self.assertIn("NOT_RUN（非 NO_TRADE）", panel)


if __name__ == "__main__":
    unittest.main()
