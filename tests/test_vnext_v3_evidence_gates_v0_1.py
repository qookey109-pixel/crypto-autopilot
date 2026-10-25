"""VNext V3 provenance guard RED tests: must fail before production code exists."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("delivery_v3", ROOT / "scripts/build_delivery_overview.py")
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


def observed_fixture() -> dict[str, object]:
    return {
        "schema": "qookey-vnext-shadow-observed-metadata-v0.1",
        "metadata_checked_date_utc": "2026-10-25",
        "source": "GITHUB_ACTIONS_EXISTING_NATURAL_RUN_METADATA_ONLY",
        "run": {
            "id": 40162915838,
            "attempt": 1,
            "event": "schedule",
            "created_at_utc": "2026-10-25T04:43:22Z",
            "head_sha": "944895170f80af21e8f9b544ec42b279c45c0d6e",
            "conclusion": "success",
        },
        "artifact": {
            "id": 12586364157,
            "name": "prospective-shadow-v0-1-40162915838-1",
            "created_at_utc": "2026-10-25T04:43:42Z",
            "digest": "sha256:191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d",
            "size_bytes": 31975,
            "expired": False,
        },
        "assurance": {
            "original_zip_content_authenticated": False,
            "source_candle_timestamp_authenticated": False,
            "feature_coverage_authenticated": False,
            "production_eligibility_proven": False,
            "additional_verified_shadow_batch": False,
            "paper_cycle_executed": False,
        },
    }


class VNextV3ProvenanceTests(unittest.TestCase):
    def test_latest_observed_run_is_not_a_seventeenth_authenticated_shadow_batch(self):
        panel = delivery.observed_shadow_metadata_panel(observed_fixture(), verified_count=16)
        self.assertIn("40162915838", panel)
        self.assertIn("12586364157", panel)
        self.assertIn("2026-10-25T04:43:22Z", panel)
        self.assertIn("2026-10-25T04:43:42Z", panel)
        self.assertIn("原始 ZIP 內容：尚未驗證", panel)
        self.assertIn("來源 K 線可用時間：UNKNOWN", panel)
        self.assertIn("16/21", panel)
        self.assertIn('href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40162915838"', panel)
        self.assertNotIn("17/21", panel)
        self.assertNotIn("正式 NO_TRADE", panel)

    def test_observed_artifact_metadata_alone_cannot_claim_verified_count(self):
        view = delivery.observed_shadow_metadata_panel(observed_fixture())
        self.assertIn("已驗證批次 UNKNOWN", view)
        self.assertNotIn("16/21", view)
        view = delivery.observed_shadow_metadata_panel(observed_fixture(), verified_count=15)
        self.assertIn("已驗證批次 UNKNOWN", view)
        self.assertNotIn("16/21", view)

    def test_false_authority_or_invalid_metadata_falls_back_to_unknown(self):
        fixture = observed_fixture()
        mutants = [
            lambda obj: obj["assurance"].update(original_zip_content_authenticated=True),
            lambda obj: obj["assurance"].update(additional_verified_shadow_batch=True),
            lambda obj: obj["run"].update(event="workflow_dispatch"),
            lambda obj: obj["run"].update(created_at_utc="2026-10-25"),
            lambda obj: obj["run"].update(head_sha="not-sha"),
            lambda obj: obj["artifact"].update(digest="sha256:not-a-hash"),
            lambda obj: obj["artifact"].update(expired=True),
            lambda obj: obj["artifact"].update(id=0),
            lambda obj: obj["artifact"].update(size_bytes=0),
        ]
        for mutate in mutants:
            changed = copy.deepcopy(fixture)
            mutate(changed)
            with self.subTest(mutate=mutate):
                text = delivery.observed_shadow_metadata_panel(changed)
                self.assertIn("UNKNOWN", text)
                self.assertNotIn("40162915838", text)
                self.assertNotIn("來源 K 線可用時間：PASS", text)
        self.assertIn("UNKNOWN", delivery.observed_shadow_metadata_panel(None))

    def test_production_not_run_cannot_be_presented_as_executed_no_trade(self):
        current = delivery.read_json(delivery.CURRENT_OPERATIONS)
        panel = delivery.market_decision_panel(current)
        self.assertIn("僅設計時原因：NO_ELIGIBLE_STRATEGY", panel)
        self.assertIn("NOT_RUN（非 NO_TRADE）", panel)
        self.assertIn("不是 runtime reason 或已發生的 NO_TRADE", panel)

    def test_wrong_or_missing_registry_does_not_promote_hypothetical_reason(self):
        current = delivery.read_json(delivery.CURRENT_OPERATIONS)
        original = delivery.read_json
        for kind in ("missing", "changed", "nonempty"):
            def fake_reader(path, root=delivery.ROOT):
                if path == "config/cloud_paper_strategy_registry_v0_1.json":
                    if kind == "missing":
                        raise FileNotFoundError("unavailable")
                    if kind == "changed":
                        data = original(path, root)
                        data["model_quality"] = "PASS"
                        return data
                    data = original(path, root)
                    data["strategies"] = [{"id": "unverified"}]
                    return data
                return original(path, root)
            with patch.object(delivery, "read_json", fake_reader):
                panel = delivery.market_decision_panel(current)
                self.assertNotIn("僅設計時原因：NO_ELIGIBLE_STRATEGY", panel)
                self.assertIn("正式原因碼：UNKNOWN", panel)


if __name__ == "__main__":
    unittest.main()
