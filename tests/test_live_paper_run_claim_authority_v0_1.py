from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-09-22-live-paper-run-slot-claim-v0-1-prepared.json"
)


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    return hashlib.sha1(framed).hexdigest()


class LivePaperRunClaimAuthorityV01Tests(unittest.TestCase):
    def test_prepared_receipt_binds_exact_files_and_does_not_self_merge(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            receipt["status"],
            "PREPARED_AWAITING_EXPLICIT_PROTECTED_MAIN_MERGE_AUTHORIZATION",
        )
        self.assertEqual(
            receipt["source_main_sha"],
            "b84ba7bd1bdc80e65a53f47a15dd9961c5152e97",
        )
        for row in receipt["bound_files"]:
            path = ROOT / row["path"]
            self.assertTrue(path.is_file(), row["path"])
            self.assertEqual(_git_blob_sha(path), row["git_blob_sha"])

        scope = receipt["prepared_scope"]
        self.assertEqual(
            scope["deterministic_slot_identity"],
            ["run_id", "sequence", "previous_step_id", "previous_state_id"],
        )
        self.assertTrue(scope["claim_write_before_provider_call"])
        self.assertFalse(scope["claim_expiry"])
        self.assertFalse(scope["automatic_claim_takeover"])
        self.assertFalse(scope["automatic_retry_after_claim_conflict"])
        self.assertTrue(scope["recovery_unresolved_claim_requires_review"])
        self.assertFalse(scope["automatic_schedule_added"])

        authority = receipt["authority"]
        self.assertTrue(authority["existing_public_live_market_data_scope_only"])
        self.assertTrue(authority["existing_paper_state_persistence_scope_only"])
        for key, value in authority.items():
            if key in {
                "existing_public_live_market_data_scope_only",
                "existing_paper_state_persistence_scope_only",
            }:
                continue
            self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
