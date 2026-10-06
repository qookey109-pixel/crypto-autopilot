from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "prospective_shadow_collection_proposal_v0_1.json"


class ProspectiveShadowCollectionProposalV01Tests(unittest.TestCase):
    def test_proposal_is_not_active_and_grants_no_runtime_authority(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["schema"],
            "qookey-prospective-shadow-collection-proposal-v0.1",
        )
        self.assertEqual(payload["status"], "PREPARED_NOT_ACTIVE")
        authority = payload["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_evidence_backend_is_explicitly_unresolved(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        backend = payload["evidence_backend"]
        self.assertEqual(backend["status"], "UNRESOLVED")
        self.assertFalse(backend["r2_write_authorized"])
        self.assertFalse(backend["d1_write_authorized"])
        self.assertFalse(backend["github_artifact_persistence_authorized"])
        self.assertFalse(backend["repository_commit_persistence_authorized"])

    def test_schedule_is_only_a_proposal(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        runtime = payload["proposed_runtime"]
        self.assertEqual(runtime["signal_snapshot_cadence"], "4H_CLOSED_BAR")
        self.assertEqual(runtime["outcome_settlement_cadence"], "HOURLY")
        self.assertEqual(runtime["observation_window_days_minimum"], 30)
        self.assertEqual(runtime["observation_window_days_target_maximum"], 90)
        self.assertFalse(payload["authority"]["schedule_authorized"])
        self.assertFalse(payload["authority"]["workflow_creation_authorized"])


if __name__ == "__main__":
    unittest.main()
