from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from crypto_autopilot.research.zec_v0_3_development_contract import (
    build_zec_v0_3_candidate_grid,
    validate_zec_v0_3_development_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "zec_strategy_v0_3_development_matrix_v0_1.json"


class ZecV03DevelopmentContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_candidate_grid_is_exactly_64_and_deterministic(self) -> None:
        first = build_zec_v0_3_candidate_grid(self.config)
        second = build_zec_v0_3_candidate_grid(self.config)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertEqual(first[0].candidate_id, "zec-v0-3-01")
        self.assertEqual(first[-1].candidate_id, "zec-v0-3-64")
        self.assertEqual(len({candidate.candidate_id for candidate in first}), 64)

    def test_contract_covers_full_already_seen_development_window(self) -> None:
        evidence = validate_zec_v0_3_development_contract(self.config)

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["candidate_count"], 64)
        self.assertEqual(evidence["development_fold_count"], 4)
        self.assertEqual(evidence["development_matrix_cells"], 256)
        self.assertFalse(evidence["fresh_confirmation_accessed"])
        self.assertFalse(evidence["fresh_confirmation_access_authorized"])
        self.assertFalse(evidence["execution_authorized"])
        self.assertFalse(evidence["live_trading_authorized"])

    def test_fresh_confirmation_authority_change_fails_closed(self) -> None:
        mutated = deepcopy(self.config)
        mutated["fresh_confirmation_window"]["access_authorized"] = True

        with self.assertRaisesRegex(ValueError, "fresh confirmation must remain unopened"):
            validate_zec_v0_3_development_contract(mutated)

    def test_fold_gap_or_overlap_fails_closed(self) -> None:
        mutated = deepcopy(self.config)
        mutated["development_window"]["folds"][1]["start_utc"] = "2023-09-01T00:00:00Z"

        with self.assertRaisesRegex(ValueError, "contiguous"):
            validate_zec_v0_3_development_contract(mutated)

    def test_selective_omission_cannot_be_enabled(self) -> None:
        mutated = deepcopy(self.config)
        mutated["development_protocol"]["selective_omission_allowed"] = True

        with self.assertRaisesRegex(ValueError, "protocol boundary"):
            validate_zec_v0_3_development_contract(mutated)

    def test_candidate_axis_drift_is_visible_in_count_contract(self) -> None:
        mutated = deepcopy(self.config)
        mutated["candidate_axes"]["account_risk_fraction"].append(0.2)

        with self.assertRaisesRegex(ValueError, "candidate axes drifted"):
            validate_zec_v0_3_development_contract(mutated)

    def test_same_size_axis_substitution_fails_closed(self) -> None:
        mutated = deepcopy(self.config)
        mutated["candidate_axes"]["macd"][1] = "10/24/8"

        with self.assertRaisesRegex(ValueError, "candidate axes drifted"):
            validate_zec_v0_3_development_contract(mutated)

    def test_frozen_window_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.config)
        mutated["fresh_confirmation_window"]["end_exclusive_utc"] = (
            "2026-09-17T00:00:00Z"
        )

        with self.assertRaisesRegex(ValueError, "temporal boundaries drifted"):
            validate_zec_v0_3_development_contract(mutated)


if __name__ == "__main__":
    unittest.main()
