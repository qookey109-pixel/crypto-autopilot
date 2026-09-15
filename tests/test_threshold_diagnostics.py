import unittest

from crypto_autopilot.training.detailed import IntradayExample
from crypto_autopilot.training.threshold_diagnostics import (
    probability_distribution,
    probability_quality,
    summarize_thresholds_across_folds,
    threshold_sweep,
)


def _example(index: int, forward_return: float) -> IntradayExample:
    return IntradayExample(
        symbol=f"S{index}",
        asset_class="crypto",
        time_ms=index,
        features=(),
        label=int(forward_return > 0),
        forward_return=forward_return,
    )


class ThresholdDiagnosticsTests(unittest.TestCase):
    def test_probability_distribution_reports_upper_tail_and_mean(self) -> None:
        distribution = probability_distribution([0.49, 0.51, 0.53, 0.56])

        self.assertEqual(distribution["count"], 4)
        self.assertEqual(distribution["minimum"], 0.49)
        self.assertAlmostEqual(distribution["mean"], 0.5225)
        self.assertEqual(distribution["p50"], 0.53)
        self.assertEqual(distribution["p90"], 0.56)
        self.assertEqual(distribution["maximum"], 0.56)

    def test_probability_quality_exposes_calibration_and_separation(self) -> None:
        items = [
            _example(1, 0.001),
            _example(2, 0.002),
            _example(3, -0.001),
            _example(4, -0.002),
        ]
        quality = probability_quality(items, [0.60, 0.55, 0.45, 0.40])

        self.assertEqual(quality["samples"], 4)
        self.assertEqual(quality["label_positive_rate"], 0.5)
        self.assertEqual(quality["mean_predicted_probability"], 0.5)
        self.assertEqual(quality["calibration_gap"], 0.0)
        self.assertAlmostEqual(quality["positive_label_mean_probability"], 0.575)
        self.assertAlmostEqual(quality["negative_label_mean_probability"], 0.425)
        self.assertAlmostEqual(quality["mean_probability_separation"], 0.15)
        self.assertEqual(quality["above_0_50_count"], 2)
        self.assertEqual(quality["above_0_50_rate"], 0.5)

    def test_threshold_sweep_exposes_zero_signal_and_selection_rate(self) -> None:
        items = [
            _example(1, 0.001),
            _example(2, 0.002),
            _example(3, -0.001),
            _example(4, 0.003),
        ]
        probabilities = [0.49, 0.51, 0.53, 0.54]
        training = {
            "probability_threshold": 0.55,
            "cost_scenarios": [
                {
                    "name": "base",
                    "fee_bps_per_side": 5.0,
                    "slippage_bps_per_side": 2.0,
                }
            ],
        }

        result = threshold_sweep(items, probabilities, training=training)

        rows = {row["threshold"]: row for row in result["rows"]}
        configured = rows[0.55]["cost_scenarios"]["base"]
        lowered = rows[0.50]["cost_scenarios"]["base"]
        self.assertEqual(configured["signal_count"], 0)
        self.assertEqual(configured["selection_rate"], 0.0)
        self.assertEqual(configured["outcome"], "ZERO_SIGNAL")
        self.assertEqual(lowered["signal_count"], 3)
        self.assertEqual(lowered["selection_rate"], 0.75)
        self.assertEqual(result["probability_distribution"]["maximum"], 0.54)
        self.assertIn("calibration_gap", result["probability_quality"])
        self.assertIs(result["diagnostic_only"], True)
        self.assertIs(result["quality_gate_changed"], False)

    def test_cross_fold_summary_rejects_threshold_with_zero_or_negative_folds(self) -> None:
        def fold(name, count, rows):
            return {
                "name": name,
                "candidate_thresholds": [0.50, 0.51],
                "probability_distribution": {"count": count},
                "rows": rows,
            }

        def row(threshold, signals, average_return):
            return {
                "threshold": threshold,
                "cost_scenarios": {
                    "base": {
                        "signal_count": signals,
                        "average_net_return": average_return,
                        "maximum_drawdown": 0.1 if signals else 0.0,
                        "maximum_symbol_concentration": 0.5 if signals else 0.0,
                    }
                },
            }

        folds = [
            fold("fold-1", 100, [row(0.50, 10, -0.01), row(0.51, 2, 0.01)]),
            fold("fold-2", 100, [row(0.50, 5, 0.02), row(0.51, 0, 0.0)]),
        ]

        summary = summarize_thresholds_across_folds(folds)
        rows = {item["threshold"]: item for item in summary["rows"]}
        self.assertEqual(rows[0.50]["status"], "REJECT_NON_POSITIVE_RETURN")
        self.assertEqual(rows[0.50]["non_positive_return_folds"], ["fold-1"])
        self.assertEqual(rows[0.51]["status"], "REJECT_ZERO_SIGNAL")
        self.assertEqual(rows[0.51]["zero_signal_folds"], ["fold-2"])
        self.assertEqual(summary["supported_thresholds"], [])
        self.assertIs(summary["threshold_change_supported"], False)
        self.assertEqual(
            summary["recommended_action"],
            "DO_NOT_CHANGE_THRESHOLD_FROM_THIS_SWEEP",
        )
        self.assertIs(summary["quality_gate_changed"], False)


if __name__ == "__main__":
    unittest.main()
