from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.binance_funding_materialization_plan_v0_2 import (
    BinanceFundingMaterializationPlanV02Error,
    build_v0_2_scope,
    canonical_scope_sha256,
    validate_v0_2_authorities,
    validate_v0_2_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/binance_funding_materialization_authority_v0_2.json"


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return payload


def authorities(config: dict[str, object]):
    return (
        load(ROOT / str(config["coverage_authority"])),
        load(ROOT / str(config["budget_authority"])),
        load(ROOT / str(config["source_proof_authority"])),
        load(ROOT / str(config["continuity_review_authority"])),
    )


class BinanceFundingMaterializationPlanV02Tests(unittest.TestCase):
    def test_real_v0_2_scope_and_hash_are_frozen(self) -> None:
        config = load(CONFIG)
        validate_v0_2_config(config)
        coverage, budget, source_proof, review = authorities(config)
        validate_v0_2_authorities(coverage, budget, source_proof, review)
        scope = build_v0_2_scope(coverage)

        self.assertEqual(scope.symbol_count, 15)
        self.assertEqual(scope.symbol_months, 1003)
        self.assertEqual(scope.canonical_objects, 94)
        self.assertEqual(
            canonical_scope_sha256(scope),
            "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58",
        )
        self.assertEqual(
            config["expected_source_checksum_set_sha256"],
            "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3",
        )

    def test_hype_2026_is_deferred_without_removing_hype_2025(self) -> None:
        config = load(CONFIG)
        coverage, *_ = authorities(config)
        scope = build_v0_2_scope(coverage)
        hype = [item for item in scope.annual_scopes if item.symbol == "HYPEUSDT"]

        self.assertEqual(len(hype), 1)
        self.assertEqual(hype[0].year, 2025)
        self.assertEqual(hype[0].months, (5, 6, 7, 8, 9, 10, 11, 12))
        self.assertFalse(
            any(item.symbol == "HYPEUSDT" and item.year == 2026 for item in scope.annual_scopes)
        )

    def test_v0_2_does_not_relax_safety_or_cadence_rules(self) -> None:
        config = load(CONFIG)
        self.assertEqual(config["materialization_cadence_jitter_tolerance_ms"], 50)
        for field in (
            "interpolation_authorized",
            "provider_splicing_authorized",
            "source_switch_authorized",
            "pionex_native_relabel_authorized",
            "historical_universe_membership_authorized",
            "backtest_admission_authorized",
            "trade_plan_authorized",
            "live_trading_authorized",
            "planning_r2_writes_authorized",
            "funding_materialization_authorized",
        ):
            self.assertIs(config[field], False)

    def test_v0_2_rejects_scope_expansion_or_tolerance_relaxation(self) -> None:
        config = load(CONFIG)
        widened = dict(config)
        widened["expected_materialized_symbol_months"] = 1010
        with self.assertRaises(BinanceFundingMaterializationPlanV02Error):
            validate_v0_2_config(widened)

        relaxed = dict(config)
        relaxed["materialization_cadence_jitter_tolerance_ms"] = 1000
        with self.assertRaises(BinanceFundingMaterializationPlanV02Error):
            validate_v0_2_config(relaxed)

    def test_continuity_review_must_keep_v0_1_blocked(self) -> None:
        config = load(CONFIG)
        coverage, budget, source_proof, review = authorities(config)
        changed = json.loads(json.dumps(review))
        changed["v0_1_materialization_effect"]["v0_1_write_execution_must_remain_blocked"] = False
        with self.assertRaises(BinanceFundingMaterializationPlanV02Error):
            validate_v0_2_authorities(coverage, budget, source_proof, changed)


if __name__ == "__main__":
    unittest.main()
