from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.challenger_promotion_v0_1 import (
    evaluate_challenger_promotion,
)


ROOT = Path(__file__).resolve().parents[1]


def _protocol() -> dict[str, object]:
    return json.loads(
        (ROOT / "config" / "challenger_promotion_protocol_v0_1.json").read_text(
            encoding="utf-8"
        )
    )


def _evidence() -> dict[str, object]:
    return {
        "integrity": {
            "lineage_complete": True,
            "no_lookahead": True,
            "provider_separated": True,
            "holdout_untouched": True,
            "formal_baseline_unchanged": True,
        },
        "walk_forward_folds": [
            {
                "ready": True,
                "out_of_sample_trades": 75,
                "net_expectancy_r": value,
            }
            for value in (0.08, 0.10, 0.07, 0.12)
        ],
        "total_out_of_sample_trades": 300,
        "cost_stress_net_expectancy_r": 0.02,
        "maximum_drawdown_pct": 20.0,
        "maximum_single_symbol_fraction": 0.10,
        "leverage_rejection_fraction": 0.20,
        "baseline_expectancy_r": 0.04,
        "challenger_expectancy_r": 0.09,
        "side_trade_counts": {"LONG": 150, "SHORT": 150},
        "regime_trade_counts": {"TREND_UP": 100, "TREND_DOWN": 100, "RANGE": 100},
    }


class ChallengerPromotionProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = _protocol()

    def test_passing_core_evidence_is_review_ready_not_promoted(self) -> None:
        result = evaluate_challenger_promotion(
            track="CORE_LONG_SHORT",
            evidence=_evidence(),
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "EVIDENCE_READY_FOR_HUMAN_REVIEW")
        self.assertEqual(result["failures"], [])
        self.assertFalse(result["authority"]["automatic_model_promotion_authorized"])
        self.assertFalse(result["authority"]["live_trading_authorized"])

    def test_weak_short_and_cost_stress_fail_closed(self) -> None:
        evidence = _evidence()
        evidence["side_trade_counts"] = {"LONG": 250, "SHORT": 50}
        evidence["cost_stress_net_expectancy_r"] = -0.01
        result = evaluate_challenger_promotion(
            track="CORE_LONG_SHORT",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("SHORT_TRADES_BELOW_GATE", result["failures"])
        self.assertIn("COST_STRESS_EXPECTANCY_BELOW_GATE", result["failures"])

    def test_holdout_integrity_failure_cannot_pass(self) -> None:
        evidence = _evidence()
        evidence["integrity"] = deepcopy(evidence["integrity"])
        evidence["integrity"]["holdout_untouched"] = False  # type: ignore[index]
        result = evaluate_challenger_promotion(
            track="CORE_LONG_SHORT",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("INTEGRITY_HOLDOUT_UNTOUCHED_FAILED", result["failures"])

    def test_tokenized_track_requires_session_action_and_spread_evidence(self) -> None:
        evidence = _evidence()
        evidence["walk_forward_folds"] = [
            {"ready": True, "out_of_sample_trades": 40, "net_expectancy_r": 0.08}
            for _ in range(4)
        ]
        evidence["total_out_of_sample_trades"] = 160
        evidence.update(
            {
                "distinct_symbols": 4,
                "session_policy_coverage": 1.0,
                "corporate_action_policy_coverage": 1.0,
                "spread_stress_pass": True,
            }
        )
        result = evaluate_challenger_promotion(
            track="TOKENIZED_EQUITY",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "EVIDENCE_READY_FOR_HUMAN_REVIEW")

    def test_protocol_itself_has_no_execution_or_promotion_authority(self) -> None:
        self.assertEqual(self.protocol["status"], "PREPARED_EVIDENCE_GATE_ONLY")
        self.assertTrue(all(value is False for value in self.protocol["authority"].values()))


if __name__ == "__main__":
    unittest.main()
