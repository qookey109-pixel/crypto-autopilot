from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.apply_dashboard_current_operations_v0_2 import overlay_current_operations


ROOT = Path(__file__).resolve().parents[1]


class DashboardCurrentOperationsOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = json.loads(
            (ROOT / "research/status/current-operations-v0-2.json").read_text(
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
                    "detail": "old current wording",
                    "status": "AUTHORIZED",
                }
            ],
            "gates": [
                {
                    "name": "V0.12 Metadata Capture",
                    "detail": "old current wording",
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

    def test_overlay_projects_current_core100_and_pionex_state(self) -> None:
        result = overlay_current_operations(copy.deepcopy(self.dashboard), self.current)
        project = result["project"]

        self.assertEqual(result["schema"], "qookey-dashboard-authority-snapshot-v0.13")
        self.assertEqual(
            project["currentOperationsReviewedMainSha"],
            "f5cf74292fca262ba72c4e0b36f8d757dfb82531",
        )
        self.assertEqual(project["core100HistoryState"], "COMPLETE_10_OF_10")
        self.assertEqual(project["core100TrainingState"], "COMPLETED_PASS")
        self.assertEqual(project["core100ModelQualityState"], "REJECT")
        self.assertEqual(
            project["core100ThresholdReplayState"],
            "COMPLETED_NO_SUPPORTED_THRESHOLD_CHANGE",
        )
        self.assertFalse(project["core100ThresholdChangeSupported"])
        self.assertEqual(
            project["pionexValidationMaterializationState"],
            "PENDING_MANUAL_DISPATCH",
        )

    def test_overlay_stops_describing_v012_as_current_capture_path(self) -> None:
        result = overlay_current_operations(copy.deepcopy(self.dashboard), self.current)
        project = result["project"]
        pipeline = {row["name"]: row for row in result["pipeline"]}
        gates = {row["name"]: row for row in result["gates"]}

        self.assertEqual(
            project["currentMetadataCaptureExecutionPath"],
            "NONE_V0_12_WINDOW_ENDED",
        )
        self.assertEqual(project["v0_12SuccessorWindowState"], "HISTORICAL_WINDOW_ENDED")
        self.assertFalse(project["v0_12CurrentWindowActive"])
        self.assertTrue(project["v0_12ScheduleRegistrationPresent"])
        self.assertFalse(project["successorMetadataCaptureExecutionAuthorized"])
        self.assertFalse(project["successorMetadataScheduleEnabled"])
        self.assertEqual(pipeline["V0.12 Successor Metadata Window"]["status"], "HISTORICAL")
        self.assertEqual(gates["V0.12 Metadata Capture"]["status"], "HISTORICAL")

    def test_overlay_preserves_closed_safety_boundaries(self) -> None:
        result = overlay_current_operations(copy.deepcopy(self.dashboard), self.current)
        project = result["project"]
        security = result["securityBoundary"]

        self.assertEqual(project["replacementHoldoutState"], "FROZEN_UNOPENED")
        self.assertFalse(project["sourceSwitchAuthorized"])
        self.assertFalse(project["tradePlanAuthorized"])
        self.assertFalse(project["liveTradingAuthorized"])
        self.assertFalse(security["authorizesMetadataCapture"])
        self.assertTrue(security["authorizesPionexValidationMaterialization"])
        self.assertFalse(security["authorizesPionexPrivateApi"])
        self.assertFalse(security["authorizesHoldoutAccess"])
        self.assertFalse(security["authorizesSourceSwitch"])
        self.assertFalse(security["authorizesTradePlans"])
        self.assertFalse(security["authorizesLiveTrading"])

    def test_overlay_adds_current_operations_as_projection_source(self) -> None:
        result = overlay_current_operations(copy.deepcopy(self.dashboard), self.current)
        self.assertIn(
            "research/status/current-operations-v0-2.json",
            result["sourceAuthorities"],
        )
        projection = result["currentOperationsProjection"]
        self.assertFalse(projection["authority"])
        self.assertEqual(projection["updated_date"], "2026-09-16")

    def test_overlay_fails_closed_if_current_authority_opens_trading(self) -> None:
        bad = copy.deepcopy(self.current)
        bad["pionex_validation"]["authority"]["live_trading"] = True
        with self.assertRaises(RuntimeError):
            overlay_current_operations(copy.deepcopy(self.dashboard), bad)


if __name__ == "__main__":
    unittest.main()
