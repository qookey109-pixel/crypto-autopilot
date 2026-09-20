from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from crypto_autopilot.research.zec_v0_3_selection_policy import (
    validate_zec_v0_3_selection_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "zec_strategy_v0_3_selection_policy_v0_1.json"


class ZecV03SelectionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_frozen_policy_is_exact_and_hash_is_deterministic(self) -> None:
        policy, first_hash = validate_zec_v0_3_selection_policy(self.payload)
        second_policy, second_hash = validate_zec_v0_3_selection_policy(self.payload)

        self.assertEqual(policy, second_policy)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(len(first_hash), 64)
        self.assertEqual(policy.minimum_realized_trades_per_fold, 30)
        self.assertEqual(policy.minimum_worst_fold_return_pct_exclusive, 0.0)
        self.assertEqual(policy.minimum_stable_neighbors, 2)
        self.assertEqual(
            policy.minimum_neighbor_worst_return_retention_fraction,
            0.75,
        )

    def test_neighbor_count_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.payload)
        mutated["stable_neighbor"]["minimum_count"] = 1

        with self.assertRaisesRegex(ValueError, "frozen at 2"):
            validate_zec_v0_3_selection_policy(mutated)

    def test_retention_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.payload)
        mutated["stable_neighbor"]["minimum_worst_return_retention_fraction"] = 0.5

        with self.assertRaisesRegex(ValueError, "frozen at 0.75"):
            validate_zec_v0_3_selection_policy(mutated)

    def test_ranking_order_drift_fails_closed(self) -> None:
        mutated = deepcopy(self.payload)
        mutated["ranking_order"][0], mutated["ranking_order"][1] = (
            mutated["ranking_order"][1],
            mutated["ranking_order"][0],
        )

        with self.assertRaisesRegex(ValueError, "ranking order drifted"):
            validate_zec_v0_3_selection_policy(mutated)

    def test_execution_or_fresh_confirmation_authority_fails_closed(self) -> None:
        for key in (
            "offline_development_runner_authorized",
            "fresh_confirmation_access_authorized",
            "live_trading_authorized",
        ):
            mutated = deepcopy(self.payload)
            mutated["authority"][key] = True
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "unsafe ZEC V0.3 selection authority"):
                    validate_zec_v0_3_selection_policy(mutated)


if __name__ == "__main__":
    unittest.main()
