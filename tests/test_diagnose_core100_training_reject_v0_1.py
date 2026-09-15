import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DiagnoseCore100TrainingRejectTests(unittest.TestCase):
    def test_reports_failing_fold_and_base_cost(self) -> None:
        metrics = {
            "schema": "binance-usdm-intraday-research-metrics-v0.1",
            "status": "PASS",
            "dataset_fingerprint": "abc123",
            "walk_forward_folds": [
                {
                    "name": "fold-1",
                    "status": "PASS",
                    "train_samples": 1000,
                    "test_samples": 200,
                    "metrics": {"log_loss": 0.61},
                    "naive_train_prevalence_baseline": {"log_loss": 0.60},
                    "beats_naive_log_loss": False,
                    "cost_scenarios": {
                        "base": {
                            "signal_count": 0,
                            "average_net_return": 0.0,
                            "diagnostic_growth": 0.0,
                            "maximum_drawdown": 0.0,
                            "maximum_symbol_concentration": 0.0,
                        },
                        "stress": {
                            "signal_count": 0,
                            "average_net_return": 0.0,
                            "diagnostic_growth": 0.0,
                            "maximum_drawdown": 0.0,
                            "maximum_symbol_concentration": 0.0,
                        },
                    },
                },
                {
                    "name": "fold-2",
                    "status": "PASS",
                    "train_samples": 1200,
                    "test_samples": 250,
                    "metrics": {"log_loss": 0.55},
                    "naive_train_prevalence_baseline": {"log_loss": 0.60},
                    "beats_naive_log_loss": True,
                    "cost_scenarios": {
                        "base": {
                            "signal_count": 15,
                            "average_net_return": 0.002,
                            "diagnostic_growth": 0.03,
                            "maximum_drawdown": 0.01,
                            "maximum_symbol_concentration": 0.2,
                        }
                    },
                },
            ],
            "model_quality_gate": {
                "status": "REJECT",
                "all_folds_ready": True,
                "all_folds_beat_naive_log_loss": False,
                "all_base_cost_scenarios_positive_average_return": False,
                "automatic_promotion": False,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            metrics_path = tmp_path / "metrics.json"
            output_path = tmp_path / "diagnosis.json"
            metrics_path.write_text(json.dumps(metrics))

            subprocess.run(
                [
                    sys.executable,
                    "scripts/diagnose_core100_training_reject_v0_1.py",
                    str(metrics_path),
                    "--output",
                    str(output_path),
                ],
                check=True,
            )

            diagnosis = json.loads(output_path.read_text())

        self.assertEqual(diagnosis["source_dataset_fingerprint"], "abc123")
        self.assertEqual(diagnosis["fold_metrics_found"], 2)
        self.assertEqual(diagnosis["failing_fold_count"], 1)
        self.assertEqual(diagnosis["failing_folds"][0]["fold"], "fold-1")
        self.assertGreater(diagnosis["failing_folds"][0]["delta_vs_naive"], 0)
        self.assertEqual(diagnosis["base_cost_scenarios_found"], 2)
        self.assertEqual(diagnosis["failing_base_cost_scenario_count"], 1)
        self.assertEqual(diagnosis["failing_base_cost_scenarios"][0]["fold"], "fold-1")
        self.assertEqual(diagnosis["zero_signal_base_cost_scenario_count"], 1)
        self.assertEqual(diagnosis["zero_signal_base_cost_scenarios"][0]["signal_count"], 0)
        self.assertIs(diagnosis["diagnostic_only"], True)
        self.assertIs(diagnosis["automatic_model_promotion_authorized"], False)
        self.assertIs(diagnosis["formal_trade_plan_authorized"], False)
        self.assertIs(diagnosis["real_money_order_authorized"], False)
        self.assertIs(diagnosis["live_trading_authorized"], False)

    def test_rejects_unknown_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metrics_path = Path(directory) / "metrics.json"
            metrics_path.write_text(json.dumps({"schema": "unknown", "status": "PASS"}))

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/diagnose_core100_training_reject_v0_1.py",
                    str(metrics_path),
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported Core100 training metrics payload", completed.stderr)


if __name__ == "__main__":
    unittest.main()
