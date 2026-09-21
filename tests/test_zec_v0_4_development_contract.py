from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from crypto_autopilot.research.zec_v0_4_development_contract import (
    build_zec_v0_4_candidate_grid,
    validate_zec_v0_4_development_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "zec_strategy_v0_4_development_matrix_v0_1.json"
SELECTION = ROOT / "config" / "zec_strategy_v0_3_selection_policy_v0_1.json"


class ZecV04DevelopmentContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.selection = json.loads(SELECTION.read_text(encoding="utf-8"))

    def validate(self, payload: dict | None = None) -> dict[str, object]:
        return validate_zec_v0_4_development_contract(
            self.config if payload is None else payload,
            selection_policy_payload=self.selection,
        )

    def test_candidate_grid_is_exactly_six_and_deterministic(self) -> None:
        first = build_zec_v0_4_candidate_grid(self.config)
        second = build_zec_v0_4_candidate_grid(self.config)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)
        self.assertEqual(first[0].candidate_id, "zec-v0-4-01")
        self.assertEqual(first[-1].candidate_id, "zec-v0-4-06")
        self.assertEqual(len({candidate.candidate_id for candidate in first}), 6)

    def test_contract_is_24_cells_and_execution_closed(self) -> None:
        evidence = self.validate()

        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["candidate_count"], 6)
        self.assertEqual(evidence["development_fold_count"], 4)
        self.assertEqual(evidence["development_matrix_cells"], 24)
        self.assertFalse(evidence["fresh_confirmation_accessed"])
        self.assertFalse(evidence["fresh_confirmation_access_authorized"])
        self.assertFalse(evidence["execution_authorized"])
        self.assertFalse(evidence["live_trading_authorized"])

    def test_v0_3_selection_policy_is_reused_without_threshold_change(self) -> None:
        evidence = self.validate()

        self.assertEqual(
            evidence["selection_policy_sha256"],
            "6484f59ee6e71156c776bfe43cdf8c4716dae74f936a164e8702e175c731250d",
        )

    def test_fresh_confirmation_cannot_be_opened(self) -> None:
        mutated = deepcopy(self.config)
        mutated["fresh_confirmation_window"]["access_authorized"] = True

        with self.assertRaisesRegex(ValueError, "fresh confirmation must remain unopened"):
            self.validate(mutated)

    def test_candidate_axis_expansion_fails_closed(self) -> None:
        mutated = deepcopy(self.config)
        mutated["candidate_axes"]["activation_regime"].append("EXTRA_REGIME")

        with self.assertRaisesRegex(ValueError, "candidate axes drifted"):
            self.validate(mutated)

    def test_risk_cannot_be_reintroduced_as_a_sweep(self) -> None:
        mutated = deepcopy(self.config)
        mutated["development_protocol"]["account_risk_sweep_allowed"] = True

        with self.assertRaisesRegex(ValueError, "development protocol drifted"):
            self.validate(mutated)

    def test_fixed_risk_cannot_be_increased(self) -> None:
        mutated = deepcopy(self.config)
        mutated["fixed_rules"]["account_risk_fraction"] = 0.025

        with self.assertRaisesRegex(ValueError, "fixed rules drifted"):
            self.validate(mutated)

    def test_selection_threshold_relaxation_fails_closed(self) -> None:
        mutated_selection = deepcopy(self.selection)
        mutated_selection["eligibility"]["minimum_worst_fold_return_pct_exclusive"] = -10

        with self.assertRaisesRegex(ValueError, "worst-fold return"):
            validate_zec_v0_4_development_contract(
                self.config,
                selection_policy_payload=mutated_selection,
            )

    def test_regime_condition_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.config)
        mutated["activation_regime_definitions"]["TREND_STACKED_MOMENTUM"][
            "required_4h_conditions"
        ].remove("macd_histogram_gt_0")

        with self.assertRaisesRegex(ValueError, "regime definitions drifted"):
            self.validate(mutated)

    def test_provider_and_r2_authority_remain_closed(self) -> None:
        for key in (
            "provider_network_access_authorized",
            "new_data_access_authorized",
            "r2_read_authorized",
            "r2_write_authorized",
            "formal_holdout_access_authorized",
            "live_trading_authorized",
        ):
            mutated = deepcopy(self.config)
            mutated["authority"][key] = True
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "unsafe ZEC V0.4 authority"):
                    self.validate(mutated)


if __name__ == "__main__":
    unittest.main()
