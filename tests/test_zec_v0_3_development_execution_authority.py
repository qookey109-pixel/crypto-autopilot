from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from crypto_autopilot.research.zec_v0_3_development_execution_authority import (
    AUTHORITY_ID,
    validate_zec_v0_3_development_execution_authority,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-21-zec-v0-3-development-one-shot-authority.json"
)


class ZecV03DevelopmentExecutionAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.bindings = dict(self.payload["bound_git_blobs"])

    def test_bound_git_blobs_match_reviewed_repository_bytes(self) -> None:
        observed = {}
        for relative in self.bindings:
            payload = (ROOT / relative).read_bytes()
            header = f"blob {len(payload)}\0".encode("ascii")
            observed[relative] = hashlib.sha1(header + payload).hexdigest()  # noqa: S324
        self.assertEqual(observed, self.bindings)

    def test_proposal_is_ineffective_until_authority_pr_is_merged(self) -> None:
        authority = validate_zec_v0_3_development_execution_authority(
            self.payload,
            authority_pr_merged=False,
            observed_blob_shas=self.bindings,
        )
        self.assertEqual(authority.authority_id, AUTHORITY_ID)
        self.assertFalse(authority.effective)
        self.assertFalse(authority.public_binance_vision_read_authorized)
        self.assertFalse(authority.offline_development_execution_authorized)

    def test_exact_merged_authority_opens_only_bounded_development(self) -> None:
        authority = validate_zec_v0_3_development_execution_authority(
            self.payload,
            authority_pr_merged=True,
            observed_blob_shas=self.bindings,
        )
        self.assertTrue(authority.effective)
        self.assertTrue(authority.public_binance_vision_read_authorized)
        self.assertTrue(authority.offline_development_execution_authorized)
        self.assertTrue(authority.aggregate_report_artifact_authorized)
        self.assertEqual(self.payload["source_scope"]["archive_count"], 48)
        self.assertEqual(self.payload["source_scope"]["row_count"], 140256)
        self.assertEqual(self.payload["execution_scope"]["development_matrix_cells"], 256)
        self.assertEqual(self.payload["execution_scope"]["maximum_runs"], 1)
        self.assertEqual(self.payload["execution_scope"]["maximum_run_attempts"], 1)
        self.assertFalse(self.payload["safety_boundary"]["fresh_confirmation_access_authorized"])
        self.assertFalse(self.payload["safety_boundary"]["r2_read_authorized"])
        self.assertFalse(self.payload["safety_boundary"]["r2_write_authorized"])
        self.assertFalse(self.payload["safety_boundary"]["live_trading_authorized"])

    def test_source_scope_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.payload)
        mutated["source_scope"]["source_month_end"] = "2026-08"
        with self.assertRaisesRegex(ValueError, "source scope drifted"):
            validate_zec_v0_3_development_execution_authority(
                mutated,
                authority_pr_merged=True,
                observed_blob_shas=self.bindings,
            )

    def test_execution_scope_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.payload)
        mutated["execution_scope"]["maximum_runs"] = 2
        with self.assertRaisesRegex(ValueError, "execution scope drifted"):
            validate_zec_v0_3_development_execution_authority(
                mutated,
                authority_pr_merged=True,
                observed_blob_shas=self.bindings,
            )

    def test_blob_binding_mismatch_fails_closed(self) -> None:
        observed = dict(self.bindings)
        first = next(iter(observed))
        observed[first] = "0" * 40
        with self.assertRaisesRegex(ValueError, "blob bindings"):
            validate_zec_v0_3_development_execution_authority(
                self.payload,
                authority_pr_merged=True,
                observed_blob_shas=observed,
            )

    def test_any_opened_safety_boundary_fails_closed(self) -> None:
        for key in self.payload["safety_boundary"]:
            mutated = deepcopy(self.payload)
            mutated["safety_boundary"][key] = True
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "safety boundary drifted"):
                    validate_zec_v0_3_development_execution_authority(
                        mutated,
                        authority_pr_merged=True,
                        observed_blob_shas=self.bindings,
                    )


if __name__ == "__main__":
    unittest.main()
