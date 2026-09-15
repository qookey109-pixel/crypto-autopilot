import unittest

from crypto_autopilot.training.detailed import IntradayExample
from crypto_autopilot.training.threshold_diagnostics import (
    probability_distribution,
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
    def test_probability_distribution_reports_upper_tail(self) -> None:
        distribution = probability_distribution([0.49, 0.51, 0.53, 0.56])

        self.assertEqual(distribution["count"], 4)
        self.assertEqual(distribution["minimum"], 0.49)
        self.assertEqual(distribution["p50"], 0.53)
        self.assertEqual(distribution["p90"], 0.56)
        self.assertEqual(distribution["maximum"], 0.56)

    def test_threshold_sweep_exposes_zero_signal_configured_threshold(self) -> None:
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
        self.assertEqual(rows[0.55]["cost_scenarios"]["base"]["signal_count"], 0)
        self.assertEqual(rows[0.50]["cost_scenarios"]["base"]["signal_count"], 3)
        self.assertEqual(result["probability_distribution"]["maximum"], 0.54)
        self.assertIs(result["diagnostic_only"], True)
        self.assertIs(result["quality_gate_changed"], False)


if __name__ == "__main__":
    unittest.main()
