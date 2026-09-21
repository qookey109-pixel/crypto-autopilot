from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from crypto_autopilot.research.zec_v0_3_development_execution_authority import (
    AUTHORITY_ID,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "zec_v0_3_execution",
    ROOT / "scripts/run_zec_v0_3_development_execution_v0_1.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class ZecV03DevelopmentExecutionScriptTests(unittest.TestCase):
    def test_frozen_month_inventory_is_exactly_48_months(self) -> None:
        periods = module._periods()
        self.assertEqual(len(periods), 48)
        self.assertEqual(periods[0], "2022-08")
        self.assertEqual(periods[-1], "2026-07")

    def test_month_bounds_cover_exact_15m_rows(self) -> None:
        total = 0
        for period in module._periods():
            start, end = module._month_bounds(period)
            self.assertEqual((end - start) % module.STEP_MS, 0)
            total += (end - start) // module.STEP_MS
        self.assertEqual(total, 140256)

    def test_wrong_authority_id_fails_before_github_or_provider_access(self) -> None:
        payload = module._read_json(module.AUTHORITY)
        with self.assertRaisesRegex(
            module.ZecV03ExecutionPreflightError,
            "authority id mismatch",
        ):
            module._verify_runtime_authority(
                payload,
                requested_authority_id=AUTHORITY_ID + "-wrong",
            )

    def test_checked_in_receipt_points_only_to_reviewed_repository_paths(self) -> None:
        payload = module._read_json(module.AUTHORITY)
        for relative in payload["bound_git_blobs"]:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
