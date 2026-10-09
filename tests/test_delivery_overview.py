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

        self.assertNotIn("每日偶數小時 :23", schedule)
        self.assertIn("Core100 研究訓練", schedule)
        self.assertIn("每週日 12:37", schedule)
        self.assertIn("NO_CHANGE", schedule)
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
        self.assertEqual(web_current["mode"], "PAPER_AND_LIVE_PAPER_ONLY")
        self.assertTrue(web_current["publicLiveMarketDataAuthorized"])
        self.assertTrue(web_current["livePaperSimulationAuthorized"])
        self.assertFalse(web_current["liveTradingAuthorized"])
        self.assertFalse(web_current["liveRealTradingAuthorized"])

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

    def test_shadow_cron_grid_is_reference_only_and_not_a_missed_trigger_claim(self) -> None:
        receipt = delivery.read_json(delivery.SHADOW_GRID_RECEIPT)
        config = delivery.read_json(
            "config/prospective_shadow_collection_execution_v0_1.json"
        )
        observed = delivery.read_json(delivery.CURRENT_OPERATIONS)[
            "vnext_delivery_checkpoint"
        ]["prospective_shadow"]["nine_batch_audit"]["natural_run_ids"]
        diagnostic = delivery.shadow_cron_grid_diagnostic(receipt, config, observed)
        self.assertEqual(diagnostic["status"], "UNDETERMINED_RUN_TO_CRON_SLOT")
        self.assertEqual(diagnostic["actual_successful_run_created_count"], 9)
        self.assertEqual(
            diagnostic["nominal_reference_slots_between_first_last_created"], 15
        )
        self.assertEqual(diagnostic["created_gaps_over_six_hours"], 5)
        self.assertEqual(
            diagnostic["run_created_gap_minutes"],
            [325, 372, 571, 344, 527, 571, 342, 529],
        )
        self.assertEqual(
            diagnostic["offset_from_latest_prior_reference_slot_min_minutes"], 61
        )
        self.assertEqual(
            diagnostic["offset_from_latest_prior_reference_slot_max_minutes"], 212
        )
        for field in (
            "grid_offset_is_actual_dispatch_delay",
            "nominal_slot_assignment_proven",
            "skipped_slot_or_root_cause_proven",
            "continuous_collection_proven",
            "production_eligibility_proven",
            "execution_authority",
        ):
            self.assertIs(diagnostic[field], False)

        for field, bad in (
            ("created_at_is_nominal_schedule_slot_identity", True),
            ("per_run_original_cron_slot_id_authenticated", True),
            ("exact_skipped_slot_identified", True),
            ("github_dispatch_delay_root_cause_proven", True),
            ("collector_failure_root_cause_proven", True),
            ("execution_authority_granted", True),
        ):
            changed = copy.deepcopy(receipt)
            changed["truth_boundaries"][field] = bad
            with self.subTest(unauthorized_claim=field), self.assertRaises(ValueError):
                delivery.shadow_cron_grid_diagnostic(changed, config, observed)

        for mutation in ("timestamp", "source", "run", "attempt", "cron"):
            changed = copy.deepcopy(receipt)
            if mutation == "timestamp":
                changed["run_metadata"][0]["created_at_utc"] = "2026-10-06T16:17:00Z"
            elif mutation == "source":
                changed["run_metadata"][0]["head_sha"] = "0" * 40
            elif mutation == "run":
                changed["run_metadata"][0]["run_id"] = 1
            elif mutation == "attempt":
                changed["run_metadata"][0]["run_attempt"] = 2
            else:
                changed["cron"]["expression_utc"] = "17 */2 * * *"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                delivery.shadow_cron_grid_diagnostic(changed, config, observed)

        changed_config = copy.deepcopy(config)
        changed_config["execution"]["cron_utc"] = "17 */2 * * *"
        with self.assertRaises(ValueError):
            delivery.shadow_cron_grid_diagnostic(receipt, changed_config, observed)
        with self.assertRaises(ValueError):
            delivery.shadow_cron_grid_diagnostic(receipt, config, observed[:-1])

    def test_market_cron_grid_fails_closed_if_receipt_is_mutated(self) -> None:
        original_reader = delivery.read_json
        current = original_reader(delivery.CURRENT_OPERATIONS)
        original_receipt = original_reader(delivery.SHADOW_GRID_RECEIPT)
        panel = delivery.market_decision_panel(current)
        self.assertIn("15 個理論時槽", panel)
        self.assertIn("61–212 分鐘", panel)
        self.assertIn("這不是已證實的 GitHub 排程延遲", panel)
        self.assertIn("9/21", panel)
        self.assertNotIn("GitHub 排程延遲已證實", panel)

        changed = copy.deepcopy(original_receipt)
        changed["truth_boundaries"]["schedule_delivery_latency_proven"] = True

        def mutated_reader(path, root=delivery.ROOT):
            if path == delivery.SHADOW_GRID_RECEIPT:
                return copy.deepcopy(changed)
            return original_reader(path, root)

        with patch.object(delivery, "read_json", mutated_reader):
            panel = delivery.market_decision_panel(current)
        self.assertIn("九批觀測需複核", panel)
        self.assertNotIn("15 個理論時槽", panel)
        self.assertNotIn("61–212 分鐘", panel)
        self.assertIn("5 段", panel)

    def test_vnext_market_panel_separates_research_from_formal_decision(self) -> None:
        current = delivery.read_json(delivery.CURRENT_OPERATIONS)
        panel = delivery.market_decision_panel(current)
        self.assertIn("MARKET PULSE", panel)
        self.assertIn("CURRENT DECISION", panel)
        self.assertIn("CANDIDATE FUNNEL", panel)
        self.assertIn("TOP MARKETS / COVERAGE", panel)
        self.assertIn("RADAR / RESEARCH", panel)
        self.assertIn("MARKET CONTEXT / SOURCE", panel)
        self.assertIn("5 個研究市場 · 非排名", panel)
        self.assertIn("逐市場事件或方向", panel)
        self.assertIn("TOP5 breadth 僅為研究 proxy", panel)
        self.assertIn("Decision Trace", panel)
        self.assertIn("5 市場 × 240 根", panel)
        self.assertIn("九批觀測需複核 · 非即時", panel)
        self.assertIn("九批資料完整性 PASS，連續性 REVIEW_REQUIRED", panel)
        self.assertIn("8,604 根重疊 K 線一致", panel)
        self.assertIn("5 段", panel)
        self.assertIn("9/21", panel)
        self.assertIn("37895797841", panel)
        self.assertIn("37893825259", panel)
        self.assertIn("37882460289", panel)
        self.assertIn("NOT_RUN（非 NO_TRADE）", panel)
        self.assertIn("UNKNOWN · 尚未投影精確來源時間", panel)
        self.assertIn("37878449661", panel)
        self.assertNotIn("今日買進", panel)

    def test_market_panel_fails_closed_on_unverified_evidence(self) -> None:
        original = delivery.read_json(delivery.CURRENT_OPERATIONS)
        for field, bad_value in (
            ("result", "REVIEW_REQUIRED"),
            ("original_archive_sha256_verified", False),
            ("consecutive_closed_candles_verified", False),
            ("execution_authority_granted", True),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed["vnext_delivery_checkpoint"]["prospective_shadow"][
                    "content_audit"
                ][field] = bad_value
                panel = delivery.market_decision_panel(changed)
                self.assertIn("UNKNOWN · 未核實", panel)
                self.assertNotIn("5 個市場各 240 根", panel)
                self.assertNotIn("單批資料驗證 PASS", panel)
                self.assertIn("Radar 研究來源未核實", panel)
                self.assertIn("UNKNOWN · 非排名", panel)

        for field, bad_value in (
            ("zip_sha256_verified_for_both", False),
            ("overlapping_identical_candles", 935),
            ("context_warmup_state", "READY"),
            ("execution_authority_granted", True),
        ):
            with self.subTest(cross_batch_field=field):
                changed = copy.deepcopy(original)
                changed["vnext_delivery_checkpoint"]["prospective_shadow"][
                    "cross_batch_audit"
                ][field] = bad_value
                panel = delivery.market_decision_panel(changed)
                self.assertIn("單批歷史觀測 · 非即時", panel)
                self.assertNotIn("936 根重疊 K 線一致", panel)
                self.assertNotIn("兩批研究驗證 PASS", panel)
                self.assertNotIn("跨批次唯讀驗證 Run #37882460289", panel)

        for field, bad_value in (
            ("status", "PASS"),
            ("zip_sha256_verified_for_all_three", False),
            ("archive_zip_sha256", ["x" * 64] * 3),
            ("natural_run_ids", [37802372751, 37846141319, 3]),
            ("overlapping_identical_candles", 2090),
            ("observed_gap_over_6h_count", 0),
            ("observed_gap_minutes", 0),
            ("uninterrupted_collection_proven", True),
            ("context_warmup_state", "READY"),
            ("paper_submission_performed", True),
            ("audit_pr_state", "MERGED"),
            ("source_main_shas", ["bad"] * 3),
        ):
            with self.subTest(three_batch_field=field):
                changed = copy.deepcopy(original)
                changed["vnext_delivery_checkpoint"]["prospective_shadow"][
                    "three_batch_audit"
                ][field] = bad_value
                panel = delivery.market_decision_panel(changed)
                self.assertIn("雙批研究驗證 · 非即時", panel)
                self.assertIn("936 根重疊 K 線一致", panel)
                self.assertNotIn("2,091 根重疊 K 線一致", panel)
                self.assertNotIn("三批觀測需複核", panel)
                self.assertNotIn("三批唯讀稽核 Run #37893825259", panel)

        changed = copy.deepcopy(original)
        changed["vnext_delivery_checkpoint"]["prospective_shadow"].pop(
            "three_batch_audit"
        )
        panel = delivery.market_decision_panel(changed)
        self.assertIn("雙批研究驗證 · 非即時", panel)
        self.assertNotIn("三批資料完整性", panel)

        for field, bad_value in (
            ("status", "PASS"),
            ("source_archive_sha256_all_nine_authenticated_in_outer_github_action", False),
            ("artifact_ids", [1] * 9),
            ("archive_zip_sha256", ["a" * 64] * 9),
            ("natural_run_ids", list(range(9))),
            ("source_main_sha_ninth", "bad"),
            ("validated_report_count", 8),
            ("overlapping_identical_candles", 8603),
            ("observed_gap_over_6h_count", 0),
            ("observed_gap_minutes", []),
            ("maximum_source_lag_minutes", 50),
            ("distinct_context_observations", 21),
            ("schedule_gap_root_cause_proven", True),
            ("original_nominal_cron_slot_mapping_authenticated", True),
            ("uninterrupted_collection_proven", True),
            ("context_warmup_state", "READY"),
            ("paper_submission_performed", True),
            ("audit_pr_state", "MERGED"),
        ):
            with self.subTest(nine_batch_field=field):
                changed = copy.deepcopy(original)
                changed["vnext_delivery_checkpoint"]["prospective_shadow"][
                    "nine_batch_audit"
                ][field] = bad_value
                panel = delivery.market_decision_panel(changed)
                self.assertIn("三批觀測需複核 · 非即時", panel)
                self.assertIn("2,091 根重疊 K 線一致", panel)
                self.assertNotIn("8,604 根重疊 K 線一致", panel)
                self.assertNotIn("九批觀測需複核", panel)
                self.assertNotIn("九批唯讀稽核 Run #37895797841", panel)

        changed = copy.deepcopy(original)
        changed["vnext_delivery_checkpoint"]["prospective_shadow"].pop(
            "nine_batch_audit"
        )
        panel = delivery.market_decision_panel(changed)
        self.assertIn("三批觀測需複核 · 非即時", panel)
        self.assertNotIn("九批資料完整性", panel)

        changed = copy.deepcopy(original)
        changed["cloudflare_prepaid_d1_runtime_gateway_v0_1"][
            "production_cycle_status"
        ] = "SUCCESS"
        panel = delivery.market_decision_panel(changed)
        self.assertIn("正式 Paper 執行狀態 UNKNOWN", panel)
        self.assertNotIn("NOT_RUN（非 NO_TRADE）", panel)

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
            current = json.loads(
                (site / "data/current-operations.json").read_text(encoding="utf-8")
            )
            self.assertIn("<!-- DELIVERY_OVERVIEW_START -->", template)
            self.assertIn("<!-- DELIVERY_SCHEDULE_START -->", template)
            self.assertIn("<!-- VNEXT_MARKET_START -->", template)
            self.assertIn("Decision Trace", generated)
            self.assertIn("正式決策尚未產生", generated)
            for href in (
                "https://app.mmt.gg/",
                "https://github.com/Edwardxlai/easyread",
                "https://yaozi.yalgo.io",
                "https://blog.cloudflare.com/clef-decision-models/",
            ):
                self.assertIn(href, generated)
            self.assertIn(f"{current['updatedDate']} 目前作業狀態", generated)
            self.assertIn("10/10 · COMPLETE", generated)
            self.assertIn("COMPLETE · PASS", generated)
            self.assertNotIn("PENDING MANUAL DISPATCH", generated)
            self.assertNotIn("8/10 分片", generated)
            self.assertNotEqual(generated, template)

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
