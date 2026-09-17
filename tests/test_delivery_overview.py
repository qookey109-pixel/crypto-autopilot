from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "delivery", ROOT / "scripts/build_delivery_overview.py"
)
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryOverviewTests(unittest.TestCase):
    def test_current_operations_drive_present_tense_counts_and_scope(self) -> None:
        summary, schedule, progress, web_current = delivery.overview()

        self.assertIn("10/10 · COMPLETE", summary)
        self.assertIn("COMPLETED · PASS", summary)
        self.assertIn("Model Quality REJECT", summary)
        self.assertIn("Pionex Validation", summary)
        self.assertIn("COMPLETE · PASS", summary)
        self.assertIn("35054729471", summary)
        self.assertIn("15 筆成交", summary)
        self.assertNotIn("PENDING MANUAL DISPATCH", summary)
        self.assertNotIn("8/10 分片", summary)
        self.assertNotIn("訓練尚未完成", summary)
        self.assertNotIn("PR #292", summary)

        self.assertIn("每日偶數小時 :23", schedule)
        self.assertIn("目前 10/10 COMPLETE", schedule)
        self.assertIn("training 已完成", schedule)
        self.assertIn("V0.12 metadata", schedule)
        self.assertIn("HISTORICAL", schedule)
        self.assertIn("Pionex Validation Dataset V0.2", schedule)
        self.assertIn("COMPLETE / PASS", schedule)

        self.assertEqual(progress["schema"], "qookey-dashboard-history-progress-v0.2")
        self.assertEqual(progress["status"], "COMPLETE")
        self.assertEqual(progress["shardsComplete"], 10)
        self.assertEqual(progress["shardCount"], 10)
        self.assertFalse(progress["historyReacquisitionRequired"])
        self.assertEqual(progress["trainingRunId"], 34918219864)
        self.assertEqual(progress["modelQualityStatus"], "REJECT")

        self.assertEqual(web_current["schema"], "qookey-current-operations-web-v0.3")
        self.assertFalse(web_current["authority"])
        self.assertEqual(web_current["repositoryAuthority"], "RESOLVE_MAIN_LIVE_AT_READ_TIME")
        self.assertFalse(web_current["evidenceBasisIsLatestMainClaim"])
        self.assertEqual(web_current["historyStatus"], "COMPLETE")
        self.assertEqual(web_current["historyCompleteShards"], 10)
        self.assertEqual(web_current["trainingStatus"], "COMPLETED_PASS")
        self.assertEqual(web_current["modelQualityStatus"], "REJECT")
        self.assertFalse(web_current["thresholdChangeSupported"])
        self.assertEqual(web_current["pionexValidationStatus"], "COMPLETE_PASS")
        self.assertEqual(web_current["pionexMaterializationRunId"], 35054729471)
        self.assertEqual(web_current["pionexSelectedMarketCount"], 197)
        self.assertEqual(web_current["pionexPartitionCount"], 682)
        self.assertEqual(web_current["holdoutState"], "FROZEN_UNOPENED")
        self.assertFalse(web_current["sourceSwitchAuthorized"])
        self.assertFalse(web_current["liveTradingAuthorized"])

    def test_current_operations_tamper_fails_closed(self) -> None:
        original = delivery.read_json
        for change in (
            "history_count",
            "training",
            "quality",
            "promotion",
            "latest_main_claim",
            "pionex_status",
            "pionex_run",
            "pionex_manifest",
            "pionex_private_api",
            "pionex_live_trading",
            "holdout",
            "source_switch",
        ):

            def mutated(path: str, root: Path = ROOT):
                value = copy.deepcopy(original(path, root))
                if path == delivery.CURRENT_OPERATIONS:
                    if change == "history_count":
                        value["core100"]["history_complete_shards"] = 8
                    elif change == "training":
                        value["core100"]["training_report_status"] = "FAIL"
                    elif change == "quality":
                        value["core100"]["model_quality_gate"]["status"] = "PASS"
                    elif change == "promotion":
                        value["core100"]["model_quality_gate"][
                            "automatic_promotion"
                        ] = True
                    elif change == "latest_main_claim":
                        value["evidence_basis"]["is_latest_main_claim"] = True
                    elif change == "pionex_status":
                        value["pionex_validation"][
                            "repository_materialization_status"
                        ] = "PASS"
                    elif change == "pionex_run":
                        value["pionex_validation"]["materialization_run_id"] = 1
                    elif change == "pionex_manifest":
                        value["pionex_validation"]["manifest_sha256"] = "bad"
                    elif change == "pionex_private_api":
                        value["pionex_validation"]["authority"]["private_api"] = True
                    elif change == "pionex_live_trading":
                        value["pionex_validation"]["authority"]["live_trading"] = True
                    elif change == "holdout":
                        value["gates"]["holdout"] = "OPEN"
                    elif change == "source_switch":
                        value["gates"]["source_switch_authorized"] = True
                return value

            with self.subTest(change=change), patch.object(
                delivery, "read_json", mutated
            ):
                with self.assertRaises(ValueError):
                    delivery.overview()

    def test_dated_readiness_remains_historical_and_fail_closed(self) -> None:
        original = delivery.read_json
        for change in ("authority", "full_ready", "btc_status", "btc_scope"):

            def mutated(path: str, root: Path = ROOT):
                value = copy.deepcopy(original(path, root))
                if path == "research/status/simulation-readiness-v0-1.json":
                    if change == "authority":
                        value["authority"] = True
                    elif change == "full_ready":
                        value["full_simulation_ready"] = True
                if path.endswith("2026-09-11-simulation-btc-fixed-sample-v0-1-pass.json"):
                    if change == "btc_status":
                        value["status"] = "FAIL"
                    elif change == "btc_scope":
                        value["scope"] = "FULL_UNIVERSE"
                return value

            with self.subTest(change=change), patch.object(
                delivery, "read_json", mutated
            ):
                with self.assertRaises(ValueError):
                    delivery.overview()

    def test_latest_historical_run_matches_frozen_pre_merge_observation(self) -> None:
        index = delivery.read_json("research/status/simulation-readiness-v0-1.json")
        history = index["binance_core_100_history"]
        evidence = delivery.read_json(history["progress_evidence"])
        frozen = delivery.read_json(
            "research/receipts/2026-09-13-cvc-1h-scheduled-failure-v0-1.json"
        )
        observation = next(
            row
            for row in frozen["scheduled_observations"]
            if row["run_id"] == history["latest_formal_run_id"]
        )
        self.assertEqual(evidence["head_sha"], observation["head_sha"])
        self.assertNotEqual(
            evidence["head_sha"], index["lifecycle_policy"]["merged_main_sha"]
        )
        for key in ("shards_complete", "shard_index", "observed_at_utc"):
            self.assertEqual(evidence["report"][key], observation[key])
        for key in (
            "symbol",
            "interval",
            "period",
            "archive_sha256",
            "row_count",
            "missing_bars",
        ):
            self.assertEqual(evidence["report"]["diagnostic"][key], observation[key])

    def test_generated_home_is_reproducible_and_missing_markers_fail(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder) / "site"
            shutil.copytree(ROOT / "web", site)
            delivery.build(site)
            first_html = (site / "index.html").read_bytes()
            first_progress = (site / "data/history-progress.json").read_bytes()
            first_current = (site / "data/current-operations.json").read_bytes()

            delivery.build(site)
            self.assertEqual(first_html, (site / "index.html").read_bytes())
            self.assertEqual(first_progress, (site / "data/history-progress.json").read_bytes())
            self.assertEqual(first_current, (site / "data/current-operations.json").read_bytes())

            progress = json.loads(first_progress)
            self.assertEqual(progress["shardsComplete"], 10)
            self.assertEqual(progress["status"], "COMPLETE")

            (site / "index.html").write_text(
                "missing template markers", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                delivery.build(site)

    def test_checked_in_web_is_template_and_generated_site_is_current(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder) / "site"
            shutil.copytree(ROOT / "web", site)
            delivery.build(site)

            generated = (site / "index.html").read_text(encoding="utf-8")
            template = (ROOT / "web/index.html").read_text(encoding="utf-8")
            self.assertIn("<!-- DELIVERY_OVERVIEW_START -->", template)
            self.assertIn("<!-- DELIVERY_SCHEDULE_START -->", template)
            self.assertIn("9/17 目前作業狀態", generated)
            self.assertIn("10/10 · COMPLETE", generated)
            self.assertIn("COMPLETE · PASS", generated)
            self.assertNotIn("PENDING MANUAL DISPATCH", generated)
            self.assertNotIn("8/10 分片", generated)
            self.assertNotEqual(generated, template)

            current = json.loads(
                (site / "data/current-operations.json").read_text(encoding="utf-8")
            )
            self.assertEqual(current["trainingRunId"], 34918219864)
            self.assertEqual(current["modelQualityStatus"], "REJECT")
            self.assertEqual(current["pionexValidationStatus"], "COMPLETE_PASS")

    def test_ctk_artifact_bytes_and_report_scope(self) -> None:
        receipt = delivery.read_json(
            "research/receipts/2026-09-12-ctk-lifecycle-v0-3-run-34687012733-evidence.json"
        )
        payload = (ROOT / receipt["report_path"]).read_bytes()
        self.assertEqual(len(payload), receipt["report_bytes"])
        self.assertEqual(hashlib.sha256(payload).hexdigest(), receipt["report_sha256"])
        report = json.loads(payload)
        config = (ROOT / "config/ctk_lifecycle_diagnosis_v0_3.json").read_bytes()
        self.assertEqual(report["config_sha256"], hashlib.sha256(config).hexdigest())
        self.assertEqual(report["status"], "LIFECYCLE_SHAPE_CHARACTERIZED")
        self.assertFalse(receipt["authority"]["lifecycle_exception"])
        self.assertEqual(receipt["handoff_discrepancy"]["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
