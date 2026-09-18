from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.strategy_library import (
    STRATEGY_LIBRARY_V0_1,
    get_strategy_family,
    strategy_family_ids,
    strategy_family_registry,
    validate_strategy_library,
)
from crypto_autopilot.strategy_router import STRATEGY_FAMILIES


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "strategy_library_v0_1.json"


class StrategyLibraryV01Tests(unittest.TestCase):
    def test_library_is_unique_and_fail_closed(self) -> None:
        validate_strategy_library()
        families = strategy_family_ids()
        self.assertEqual(len(families), 6)
        self.assertEqual(len(set(families)), len(families))

    def test_router_uses_the_governed_registry(self) -> None:
        self.assertEqual(STRATEGY_FAMILIES, strategy_family_ids())

    def test_every_family_remains_research_only(self) -> None:
        for spec in STRATEGY_LIBRARY_V0_1:
            with self.subTest(family=spec.family):
                self.assertFalse(spec.strategy_edge_claimed)
                self.assertFalse(spec.position_sizing_authorized)
                self.assertFalse(spec.paper_execution_authorized)
                self.assertFalse(spec.live_execution_authorized)
                self.assertEqual(spec.reusable_scope, "MULTI_ASSET_RESEARCH")
                self.assertTrue(spec.generalization_required)

    def test_machine_readable_contract_matches_code_registry(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        expected = [
            {
                "family": spec.family,
                "category": spec.category,
                "attention_profiles": list(spec.attention_profiles),
                "directions": list(spec.directions),
                "requires_market_structure": spec.requires_market_structure,
                "validation_state": spec.validation_state,
                "reusable_scope": spec.reusable_scope,
                "generalization_required": spec.generalization_required,
            }
            for spec in STRATEGY_LIBRARY_V0_1
        ]
        self.assertEqual(payload["families"], expected)

    def test_registry_lookup_is_explicit(self) -> None:
        registry = strategy_family_registry()
        self.assertEqual(tuple(registry), strategy_family_ids())
        self.assertEqual(
            get_strategy_family("MEAN_REVERSION").attention_profiles,
            ("RANGE_EXTREMITY",),
        )
        with self.assertRaises(ValueError):
            get_strategy_family("ZEC_V0_3")

    def test_single_asset_modules_are_not_silently_registered(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertFalse(
            payload["single_asset_boundary"]["zec_v0_3_registered_as_reusable_family"]
        )
        self.assertNotIn("ZEC_V0_3", strategy_family_ids())


if __name__ == "__main__":
    unittest.main()
