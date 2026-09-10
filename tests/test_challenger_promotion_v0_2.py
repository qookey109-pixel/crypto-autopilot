from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.challenger_promotion_v0_2 import (
    evaluate_challenger_promotion_v0_2,
)


ROOT = Path(__file__).resolve().parents[1]


def _protocol() -> dict[str, object]:
    return json.loads(
        (ROOT / "config" / "challenger_promotion_protocol_v0_2.json").read_text(
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
            "experiment_preregistered": True,
            "family_registry_locked": True,
            "primary_metric_frozen": True,
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
        "out_of_sample_calendar_days": 365,
        "prospective_paper_days": 35,
        "cost_stress_net_expectancy_r": 0.02,
        "maximum_drawdown_pct": 20.0,
        "maximum_single_symbol_fraction": 0.10,
        "leverage_rejection_fraction": 0.20,
        "baseline_expectancy_r": 0.04,
        "challenger_expectancy_r": 0.09,
        "side_trade_counts": {"LONG": 150, "SHORT": 150},
        "regime_trade_counts": {"TREND_UP": 100, "TREND_DOWN": 100, "RANGE": 100},
        "primary_metric": "net_expectancy_r_after_costs",
        "block_bootstrap": {
            "method": "STATIONARY_BLOCK_BOOTSTRAP",
            "replicates": 5000,
            "confidence_level": 0.95,
            "serial_dependence_preserved": True,
            "primary_metric_lower_confidence_bound_r": 0.01,
            "p_value": 0.005,
        },
        "experiment_family": {
            "family_id": "CORE_INTRADAY_DIRECTIONAL_V0_1",
            "registry_sha256": "61ad788976b6808c834521fd4bd6ad766eb0d480689d0e5bd949dada0d764f0a",
            "challenger_id": "integrated-v0-3",
            "registered_challenger_ids": [
                "sstate-baseline-v0-1",
                "paper-training-v0-1",
                "paper-exploration-v0-2",
                "long-short-v0-2",
                "integrated-v0-3",
            ],
            "p_values": {
                "sstate-baseline-v0-1": 0.20,
                "paper-training-v0-1": 0.04,
                "paper-exploration-v0-2": 0.03,
                "long-short-v0-2": 0.03,
                "integrated-v0-3": 0.005,
            },
            "evaluation_look_index": 1,
        },
        "sstate_gate_calibration": {
            "ready": True,
            "holm_adjusted_pass": True,
            "holdout_untouched": True,
            "selected_effective_samples": 100,
            "outer_fold_count": 4,
            "wilson_lower_bound": 0.52,
        },
        "short_score_calibration": {
            "ready": True,
            "independent_from_formal_long_weights": True,
            "out_of_sample_trades": 120,
            "funding_stress_pass": True,
            "squeeze_regime_evaluated": True,
        },
    }


class ChallengerPromotionV02Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = _protocol()

    def test_preregistered_multiplicity_adjusted_evidence_is_review_ready(self) -> None:
        result = evaluate_challenger_promotion_v0_2(
            track="CORE_LONG_SHORT",
            evidence=_evidence(),
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "EVIDENCE_READY_FOR_HUMAN_REVIEW")
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["metrics"]["holm_adjusted_p_value"], 0.025)
        self.assertFalse(result["authority"]["automatic_model_promotion_authorized"])

    def test_holm_bonferroni_blocks_lucky_family_winner(self) -> None:
        evidence = _evidence()
        evidence["block_bootstrap"] = deepcopy(evidence["block_bootstrap"])
        evidence["block_bootstrap"]["p_value"] = 0.03  # type: ignore[index]
        evidence["experiment_family"] = deepcopy(evidence["experiment_family"])
        evidence["experiment_family"]["p_values"] = {  # type: ignore[index]
            "integrated-v0-3": 0.03,
            "long-short-v0-2": 0.01,
            "paper-exploration-v0-2": 0.04,
            "paper-training-v0-1": 0.08,
            "sstate-baseline-v0-1": 0.20,
        }
        result = evaluate_challenger_promotion_v0_2(
            track="CORE_LONG_SHORT",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("HOLM_BONFERRONI_GATE_FAILED", result["failures"])

    def test_short_and_sstate_calibration_are_hard_review_gates(self) -> None:
        evidence = _evidence()
        evidence["sstate_gate_calibration"] = deepcopy(
            evidence["sstate_gate_calibration"]
        )
        evidence["sstate_gate_calibration"]["ready"] = False  # type: ignore[index]
        evidence["sstate_gate_calibration"][  # type: ignore[index]
            "selected_effective_samples"
        ] = 50
        evidence["short_score_calibration"] = deepcopy(
            evidence["short_score_calibration"]
        )
        evidence["short_score_calibration"]["ready"] = False  # type: ignore[index]
        result = evaluate_challenger_promotion_v0_2(
            track="CORE_LONG_SHORT",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("SSTATE_GATE_CALIBRATION_NOT_READY", result["failures"])
        self.assertIn("SSTATE_EFFECTIVE_SAMPLES_BELOW_GATE", result["failures"])
        self.assertIn("SHORT_SCORE_NOT_INDEPENDENTLY_CALIBRATED", result["failures"])

    def test_tokenized_track_uses_same_family_and_sstate_guards(self) -> None:
        evidence = _evidence()
        evidence["walk_forward_folds"] = [
            {"ready": True, "out_of_sample_trades": 40, "net_expectancy_r": 0.08}
            for _ in range(4)
        ]
        evidence["total_out_of_sample_trades"] = 160
        evidence["block_bootstrap"] = deepcopy(evidence["block_bootstrap"])
        evidence["block_bootstrap"]["p_value"] = 0.01  # type: ignore[index]
        evidence["experiment_family"] = {
            "family_id": "TOKENIZED_EQUITY_V0_1",
            "registry_sha256": "61ad788976b6808c834521fd4bd6ad766eb0d480689d0e5bd949dada0d764f0a",
            "challenger_id": "integrated-tokenized-v0-3",
            "registered_challenger_ids": [
                "tokenized-equity-v0-1",
                "integrated-tokenized-v0-3",
            ],
            "p_values": {
                "tokenized-equity-v0-1": 0.04,
                "integrated-tokenized-v0-3": 0.01,
            },
            "evaluation_look_index": 1,
        }
        evidence.update(
            {
                "distinct_symbols": 4,
                "session_policy_coverage": 1.0,
                "corporate_action_policy_coverage": 1.0,
                "spread_stress_pass": True,
            }
        )
        result = evaluate_challenger_promotion_v0_2(
            track="TOKENIZED_EQUITY",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "EVIDENCE_READY_FOR_HUMAN_REVIEW")

    def test_duration_and_bootstrap_lower_bound_fail_closed(self) -> None:
        evidence = _evidence()
        evidence["prospective_paper_days"] = 10
        evidence["block_bootstrap"] = deepcopy(evidence["block_bootstrap"])
        evidence["block_bootstrap"][  # type: ignore[index]
            "primary_metric_lower_confidence_bound_r"
        ] = 0.0
        result = evaluate_challenger_promotion_v0_2(
            track="CORE_LONG_SHORT",
            evidence=evidence,
            protocol=self.protocol,
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("PROSPECTIVE_PAPER_DAYS_BELOW_GATE", result["failures"])
        self.assertIn(
            "PRIMARY_METRIC_LOWER_CONFIDENCE_BOUND_BELOW_GATE", result["failures"]
        )

    def test_calibration_protocols_never_change_formal_authority(self) -> None:
        for filename in (
            "sstate_gate_calibration_v0_1.json",
            "short_score_calibration_v0_1.json",
        ):
            config = json.loads((ROOT / "config" / filename).read_text(encoding="utf-8"))
            self.assertTrue(all(value is False for value in config["authority"].values()))


if __name__ == "__main__":
    unittest.main()
