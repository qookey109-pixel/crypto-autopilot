from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.apply_dashboard_current_operations_v0_3 import overlay_current_operations
from scripts.build_delivery_overview import build as build_delivery_overview


ROOT = Path(__file__).resolve().parents[1]


class DashboardCurrentOperationsV03Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = json.loads(
            (ROOT / "research/status/current-operations-v0-3.json").read_text(
                encoding="utf-8"
            )
        )
        self.dashboard = {
            "authority": False,
            "locale": "zh-Hant-TW",
            "schema": "qookey-dashboard-authority-snapshot-v0.12",
            "project": {
                "mode": "PAPER-ONLY",
                "successorMetadataCaptureExecutionAuthorized": True,
                "successorMetadataScheduleEnabled": True,
                "currentMetadataCaptureExecutionPath": "github_hosted_ubuntu_v0_12",
                "liveTradingAuthorized": False,
            },
            "pipeline": [
                {
                    "name": "V0.12 Successor Metadata Window",
                    "detail": "historical overlay still marks old execution state",
                    "status": "AUTHORIZED",
                }
            ],
            "gates": [
                {
                    "name": "V0.12 Metadata Capture",
                    "detail": "historical overlay still marks old execution state",
                    "status": "AUTHORIZED",
                    "tone": "pass",
                    "critical": False,
                }
            ],
            "securityBoundary": {
                "containsSecrets": False,
                "containsPrivateExchangeResponses": False,
                "authorizesMetadataCapture": True,
                "authorizesHoldoutAccess": False,
                "authorizesSourceSwitch": False,
                "authorizesTradePlans": False,
                "authorizesLiveTrading": False,
            },
            "sourceAuthorities": [],
        }

    def test_overlay_uses_evidence_basis_without_claiming_latest_main(self) -> None:
        result = overlay_current_operations(copy.deepcopy(self.dashboard), self.current)
        project = result["project"]
        projection = result["currentOperationsProjection"]

        self.assertEqual(result["schema"], "qookey-dashboard-authority-snapshot-v0.13")
        self.assertEqual(
            project["currentOperationsEvidenceBasisSemantics"],
            "REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION",
        )
        self.assertFalse(project["currentOperationsEvidenceBasisIsLatestMainClaim"])
        self.assertFalse(projection["is_latest_main_claim"])
        self.assertEqual(
            projection["evidence_basis_parent_main_sha"],
            "3422efc91cfd973ab1991080186fb8300d26a2a5",
        )

    def test_overlay_projects_current_lifecycle_and_closes_expired_v012(self) -> None:
        result = overlay_current_operations(copy.deepcopy(self.dashboard), self.current)
        project = result["project"]
        pipeline = {row["name"]: row for row in result["pipeline"]}
        gates = {row["name"]: row for row in result["gates"]}
        security = result["securityBoundary"]

        self.assertEqual(project["core100HistoryState"], "COMPLETE_10_OF_10")
        self.assertEqual(project["core100TrainingState"], "COMPLETED_PASS")
        self.assertEqual(project["core100TrainingRunId"], 34918219864)
        self.assertEqual(project["core100ModelQualityState"], "REJECT")
        self.assertEqual(
            project["core100ThresholdReplayState"],
            "COMPLETED_NO_SUPPORTED_THRESHOLD_CHANGE",
        )
        self.assertFalse(project["core100ThresholdChangeSupported"])
        self.assertEqual(
            project["pionexValidationMaterializationState"],
            "COMPLETE_PASS",
        )
        self.assertEqual(project["pionexValidationMaterializationRunId"], 35054729471)
        self.assertEqual(project["pionexValidationSelectedMarkets"], 197)
        self.assertEqual(project["pionexValidationPartitions"], 682)
        self.assertTrue(project["pionexValidationManualDispatchOnly"])
        self.assertEqual(
            project["currentMetadataCaptureExecutionPath"],
            "NONE_V0_12_WINDOW_ENDED",
        )
        self.assertEqual(project["v0_12SuccessorWindowState"], "HISTORICAL_WINDOW_ENDED")
        self.assertFalse(project["v0_12CurrentWindowActive"])
        self.assertTrue(project["v0_12ScheduleRegistrationPresent"])
        self.assertFalse(project["successorMetadataCaptureExecutionAuthorized"])
        self.assertFalse(project["successorMetadataScheduleEnabled"])
        self.assertEqual(project["replacementHoldoutState"], "FROZEN_UNOPENED")
        self.assertFalse(project["sourceSwitchAuthorized"])
        self.assertEqual(project["mode"], "PAPER / LIVE-PAPER ONLY")
        self.assertTrue(project["publicLiveMarketDataAuthorized"])
        self.assertTrue(project["livePaperSimulationAuthorized"])
        self.assertTrue(project["paperStatePersistenceAuthorized"])
        self.assertFalse(project["liveTradingAuthorized"])
        self.assertFalse(project["liveRealTradingAuthorized"])

        self.assertEqual(pipeline["Core100 History"]["status"], "COMPLETE")
        self.assertEqual(pipeline["Core100 Training"]["status"], "COMPLETED")
        self.assertEqual(
            pipeline["Core100 Threshold Replay"]["status"], "COMPLETED_NO_CHANGE"
        )
        self.assertEqual(
            pipeline["Pionex Validation Dataset V0.2"]["status"],
            "COMPLETE_PASS",
        )
        self.assertEqual(
            pipeline["V0.12 Successor Metadata Window"]["status"], "HISTORICAL"
        )
        self.assertEqual(
            pipeline["Live Paper Simulation V0.1"]["status"],
            "LIVE_PAPER_AUTHORIZED",
        )
        self.assertEqual(gates["Core100 Model Quality"]["status"], "REJECT")
        self.assertEqual(gates["V0.12 Metadata Capture"]["status"], "HISTORICAL")
        self.assertEqual(
            gates["Pionex Repository Validation"]["status"],
            "COMPLETE_PASS",
        )
        self.assertEqual(gates["Replacement Holdout"]["status"], "NOT_AUTHORIZED")

        self.assertFalse(security["authorizesMetadataCapture"])
        self.assertTrue(security["authorizesPionexValidationMaterialization"])
        self.assertFalse(security["authorizesPionexPrivateApi"])
        self.assertFalse(security["authorizesHoldoutAccess"])
        self.assertFalse(security["authorizesSourceSwitch"])
        self.assertFalse(security["authorizesTradePlans"])
        self.assertTrue(security["authorizesLivePaperSimulation"])
        self.assertTrue(security["authorizesPaperStatePersistence"])
        self.assertFalse(security["authorizesLiveTrading"])

    def test_homepage_build_removes_stale_present_tense_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / "site"
            shutil.copytree(ROOT / "web", site)
            build_delivery_overview(site, ROOT)

            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("9/18 目前作業狀態", html)
            self.assertIn("10/10 · COMPLETE", html)
            self.assertIn("COMPLETED · PASS", html)
            self.assertIn("Model Quality REJECT", html)
            self.assertIn("Pionex Validation", html)
            self.assertIn("COMPLETE · PASS", html)
            self.assertIn("35054729471", html)
            self.assertIn("current-operations.js?v=current-ops-v0-3", html)
            self.assertNotIn("PENDING MANUAL DISPATCH", html)
            self.assertNotIn("8/10 分片", html)
            self.assertNotIn("訓練尚未完成", html)
            self.assertNotIn("PR #292", html)
            self.assertNotIn("目前因歷史補齊失敗而告警", html)

            web_current = json.loads(
                (site / "data/current-operations.json").read_text(encoding="utf-8")
            )
            self.assertEqual(web_current["schema"], "qookey-current-operations-web-v0.3")
            self.assertFalse(web_current["authority"])
            self.assertEqual(web_current["historyStatus"], "COMPLETE")
            self.assertEqual(web_current["historyCompleteShards"], 10)
            self.assertEqual(web_current["historyTotalShards"], 10)
            self.assertEqual(web_current["trainingStatus"], "COMPLETED_PASS")
            self.assertEqual(web_current["modelQualityStatus"], "REJECT")
            self.assertFalse(web_current["thresholdChangeSupported"])
            self.assertEqual(web_current["pionexValidationStatus"], "COMPLETE_PASS")
            self.assertEqual(web_current["pionexMaterializationRunId"], 35054729471)
            self.assertEqual(web_current["holdoutState"], "FROZEN_UNOPENED")
            self.assertFalse(web_current["sourceSwitchAuthorized"])
            self.assertEqual(
                web_current["mode"],
                "PAPER_AND_LIVE_PAPER_ONLY",
            )
            self.assertTrue(web_current["publicLiveMarketDataAuthorized"])
            self.assertTrue(web_current["livePaperSimulationAuthorized"])
            self.assertFalse(web_current["liveTradingAuthorized"])
            self.assertFalse(web_current["liveRealTradingAuthorized"])
            self.assertFalse(web_current["evidenceBasisIsLatestMainClaim"])

            history = json.loads(
                (site / "data/history-progress.json").read_text(encoding="utf-8")
            )
            self.assertEqual(history["schema"], "qookey-dashboard-history-progress-v0.2")
            self.assertEqual(history["status"], "COMPLETE")
            self.assertEqual(history["shardsComplete"], 10)
            self.assertFalse(history["historyReacquisitionRequired"])

    def test_overlay_fails_closed_if_current_status_claims_latest_main(self) -> None:
        bad = copy.deepcopy(self.current)
        bad["evidence_basis"]["is_latest_main_claim"] = True
        with self.assertRaises(RuntimeError):
            overlay_current_operations(copy.deepcopy(self.dashboard), bad)

    def test_overlay_fails_closed_if_pionex_completion_evidence_drifts(self) -> None:
        bad = copy.deepcopy(self.current)
        bad["pionex_validation"]["materialization_run_id"] = 1
        with self.assertRaises(RuntimeError):
            overlay_current_operations(copy.deepcopy(self.dashboard), bad)

    def test_overlay_fails_closed_if_live_trading_opens(self) -> None:
        bad = copy.deepcopy(self.current)
        bad["pionex_validation"]["authority"]["live_trading"] = True
        with self.assertRaises(RuntimeError):
            overlay_current_operations(copy.deepcopy(self.dashboard), bad)


if __name__ == "__main__":
    unittest.main()
