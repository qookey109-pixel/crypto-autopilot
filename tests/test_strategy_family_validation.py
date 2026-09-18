from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.strategy_family_validation import (
    StrategyFamilyValidationError,
    family_edge_receipt_from_report,
    policy_from_config,
    validate_strategy_family,
    validate_strategy_library_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "strategy_family_validation_v0_1.json"


def edge_report(
    index: int,
    *,
    verdict: str = "PASS",
    provider: str = "synthetic_fixture",
    research_evidence_only: object = True,
) -> dict[str, object]:
    return {
        "schema": "qookey-strategy-edge-validation-report-v0.1",
        "verdict": verdict,
        "input_fingerprint": f"{index + 1:064x}",
        "provider": provider,
        "selected_candidate_id": f"candidate-{index}",
        "reasons": (
            ["all_frozen_edge_gates_pass"]
            if verdict == "PASS"
            else ["synthetic_rejection"]
        ),
        "policy": {},
        "methods": {},
        "authority": {
            "research_evidence_only": research_evidence_only,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "promotion_authority": 0,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
            "v0_10_production_critical_path_mutated": False,
        },
        "limitations": [],
    }


def receipt(
    index: int,
    *,
    family: str = "TREND_FOLLOWING",
    symbol: str,
    regime: str,
    direction: str = "LONG",
    verdict: str = "PASS",
    provider: str = "synthetic_fixture",
):
    return family_edge_receipt_from_report(
        family=family,
        symbol=symbol,
        regime_state=regime,
        direction=direction,
        edge_report=edge_report(index, verdict=verdict, provider=provider),
    )


def ready_receipts():
    return (
        receipt(0, symbol="BTC_USDT_PERP", regime="BTC_CONCENTRATION"),
        receipt(1, symbol="ETH_USDT_PERP", regime="BTC_CONCENTRATION"),
        receipt(2, symbol="SOL_USDT_PERP", regime="BTC_CONCENTRATION"),
        receipt(3, symbol="BTC_USDT_PERP", regime="MIXED"),
        receipt(4, symbol="ETH_USDT_PERP", regime="MIXED"),
        receipt(5, symbol="SOL_USDT_PERP", regime="MIXED"),
    )


class StrategyFamilyValidationV01Tests(unittest.TestCase):
    def test_ready_requires_existing_edge_pass_across_assets_and_regimes(self) -> None:
        report = validate_strategy_family("TREND_FOLLOWING", ready_receipts())

        self.assertEqual(report["state"], "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["coverage"]["receipt_count"], 6)
        self.assertEqual(len(report["coverage"]["distinct_assets"]), 3)
        self.assertEqual(len(report["coverage"]["distinct_regimes"]), 2)
        self.assertFalse(report["authority"]["strategy_edge_claimed"])
        self.assertEqual(report["authority"]["promotion_authority"], 0)

    def test_insufficient_cross_asset_coverage_does_not_pass(self) -> None:
        receipts = (
            receipt(0, symbol="BTC_USDT_PERP", regime="BTC_CONCENTRATION"),
            receipt(1, symbol="ETH_USDT_PERP", regime="BTC_CONCENTRATION"),
            receipt(2, symbol="BTC_USDT_PERP", regime="MIXED"),
            receipt(3, symbol="ETH_USDT_PERP", regime="MIXED"),
            receipt(4, symbol="BTC_USDT_PERP", regime="ALT_EXPANSION"),
            receipt(5, symbol="ETH_USDT_PERP", regime="ALT_EXPANSION"),
        )

        report = validate_strategy_family("TREND_FOLLOWING", receipts)

        self.assertEqual(report["state"], "INSUFFICIENT_GENERALIZATION_COVERAGE")
        self.assertIn("distinct_assets_below_minimum", report["reasons"])

    def test_any_child_edge_reject_fails_family_review(self) -> None:
        receipts = list(ready_receipts())
        receipts[-1] = receipt(
            5,
            symbol="SOL_USDT_PERP",
            regime="MIXED",
            verdict="REJECT",
        )

        report = validate_strategy_family("TREND_FOLLOWING", receipts)

        self.assertEqual(report["state"], "REJECT")
        self.assertEqual(report["coverage"]["failed_edge_report_count"], 1)
        self.assertIn("one_or_more_strategy_edge_reports_rejected", report["reasons"])

    def test_provider_mixing_fails_closed(self) -> None:
        receipts = list(ready_receipts())
        receipts[-1] = receipt(
            5,
            symbol="SOL_USDT_PERP",
            regime="MIXED",
            provider="different_provider",
        )

        report = validate_strategy_family("TREND_FOLLOWING", receipts)

        self.assertEqual(report["state"], "REJECT")
        self.assertIn("provider_provenance_mixed", report["reasons"])

    def test_duplicate_receipts_are_rejected(self) -> None:
        receipts = list(ready_receipts())
        receipts[-1] = receipts[0]

        with self.assertRaises(StrategyFamilyValidationError):
            validate_strategy_family("TREND_FOLLOWING", receipts)

    def test_edge_authority_boolean_types_are_strict(self) -> None:
        with self.assertRaises(StrategyFamilyValidationError):
            family_edge_receipt_from_report(
                family="TREND_FOLLOWING",
                symbol="BTC_USDT_PERP",
                regime_state="MIXED",
                direction="LONG",
                edge_report=edge_report(0, research_evidence_only="true"),
            )

    def test_library_summary_does_not_rank_or_select_a_winner(self) -> None:
        trend = ready_receipts()
        momentum = tuple(
            receipt(
                index + 10,
                family="MOMENTUM",
                symbol=symbol,
                regime=regime,
            )
            for index, (symbol, regime) in enumerate(
                (
                    ("BTC_USDT_PERP", "BTC_CONCENTRATION"),
                    ("ETH_USDT_PERP", "BTC_CONCENTRATION"),
                    ("SOL_USDT_PERP", "BTC_CONCENTRATION"),
                    ("BTC_USDT_PERP", "MIXED"),
                    ("ETH_USDT_PERP", "MIXED"),
                    ("SOL_USDT_PERP", "MIXED"),
                )
            )
        )

        report = validate_strategy_library_evidence(trend + momentum)

        self.assertEqual(
            report["families_evaluated"], ["MOMENTUM", "TREND_FOLLOWING"]
        )
        self.assertFalse(report["ranking_performed"])
        self.assertFalse(report["winner_selected"])
        self.assertEqual(
            report["state_counts"]["FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW"], 2
        )

    def test_config_policy_is_strict_and_matches_frozen_defaults(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        policy = policy_from_config(payload)

        self.assertEqual(policy.minimum_receipts, 6)
        self.assertEqual(policy.minimum_distinct_assets, 3)
        self.assertEqual(policy.minimum_distinct_regimes, 2)
        self.assertTrue(policy.require_single_provider)
        self.assertTrue(policy.require_all_edge_pass)

        bad_payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad_payload["policy"]["require_single_provider"] = "true"
        with self.assertRaises(StrategyFamilyValidationError):
            policy_from_config(bad_payload)


if __name__ == "__main__":
    unittest.main()
