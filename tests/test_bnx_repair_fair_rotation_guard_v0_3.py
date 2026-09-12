from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from crypto_autopilot.history import bnx_repair_bundle_v0_3 as bundle

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "bnx_repair_fair_rotation_guard_v0_3_wrapper",
    ROOT / "scripts/run_bnx_repair_bundle_v0_3.py",
)
wrapper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wrapper)


class BnxRepairFairRotationGuardV03Tests(unittest.TestCase):
    def setUp(self):
        wrapper._repair_adapter.contract = None
        self.completed = [0, 1, 2, 4, 5, 6, 7]
        self.attempts = [
            {
                "sequence": 0,
                "run_id": "prior-quality-reject",
                "shard_index": 3,
                "outcome": "QUALITY_REJECT",
            }
        ]

    def test_normal_rotation_is_unchanged_without_loaded_repair_contract(self):
        selected = wrapper._original_choose_shard(10, self.completed, self.attempts)
        self.assertEqual(selected, 8)
        self.assertEqual(wrapper.choose_shard(10, self.completed, self.attempts), 8)

    def test_exact_loaded_bundle_can_retry_only_its_bound_shard(self):
        wrapper._repair_adapter.contract = {"v0_1": {}, "v0_2": {}, "v0_3": {}}
        self.assertEqual(wrapper.choose_shard(10, self.completed, self.attempts), 3)
        self.assertTrue(bundle.RECOVERY_FAIR_ROTATION_OVERRIDE_AUTHORIZED)

    def test_override_fails_closed_for_completed_shard_or_bad_contract(self):
        wrapper._repair_adapter.contract = {"v0_1": {}, "v0_2": {}, "v0_3": {}}
        with self.assertRaisesRegex(bundle.RepairAuthorityError, "SHARD_ALREADY_COMPLETE"):
            wrapper.choose_shard(10, [0, 1, 2, 3, 4, 5, 6, 7], self.attempts)

        wrapper._repair_adapter.contract = {"v0_1": {}, "v0_2": {}}
        with self.assertRaisesRegex(bundle.RepairAuthorityError, "CONTRACT_MISMATCH"):
            wrapper.choose_shard(10, self.completed, self.attempts)

    def test_authority_helper_rejects_any_other_requested_shard(self):
        contract = {"v0_1": {}, "v0_2": {}, "v0_3": {}}
        with self.assertRaisesRegex(bundle.RepairAuthorityError, "SHARD_MISMATCH"):
            bundle.authorize_recovery_shard_override(
                contract,
                requested_shard=4,
                completed=self.completed,
            )


if __name__ == "__main__":
    unittest.main()
