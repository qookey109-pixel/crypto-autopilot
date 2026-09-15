from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import crypto_autopilot.training.detailed as detailed_training
from crypto_autopilot.training.detailed import IntradayExample


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "train_binance_detailed_history_models_v0_2.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "train_binance_detailed_history_models_v0_2_contract_test",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _example(index: int, probability_side_return: float) -> IntradayExample:
    return IntradayExample(
        symbol=f"S{index}",
        asset_class="crypto",
        time_ms=1_000 + index,
        features=(),
        label=int(probability_side_return > 0.0),
        forward_return=probability_side_return,
    )


class DetailedTrainingThresholdIntegrationTests(unittest.TestCase):
    def test_wrapper_adds_diagnostics_without_mutating_quality_gate(self) -> None:
        module = _load_script_module()
        original_signal_diagnostics = detailed_training._signal_diagnostics
        items = [
            _example(1, 0.003),
            _example(2, 0.002),
            _example(3, -0.001),
            _example(4, 0.004),
        ]
        probabilities = [0.49, 0.51, 0.53, 0.54]
        configured_gate = {
            "status": "REJECT",
            "all_folds_ready": True,
            "all_folds_beat_naive_log_loss": False,
            "all_base_cost_scenarios_positive_average_return": False,
            "automatic_promotion": False,
        }
        fake_metrics = {
            "walk_forward_folds": [
                {
                    "name": "fold-1",
                    "status": "PASS",
                    "beats_naive_log_loss": False,
                    "cost_scenarios": {
                        "base": {
                            "signal_count": 0,
                            "average_net_return": 0.0,
                        }
                    },
                }
            ],
            "model_quality_gate": dict(configured_gate),
        }

        def fake_run_intraday_training(
            examples,
            *,
            config,
            dataset_fingerprint: str,
            generated_at_utc: str,
        ):
            self.assertEqual(examples, items)
            self.assertEqual(dataset_fingerprint, "dataset-sha")
            self.assertEqual(generated_at_utc, "2026-09-15T00:00:00Z")
            result = detailed_training._signal_diagnostics(
                items,
                probabilities,
                threshold=float(config["training"]["probability_threshold"]),
                fee_bps_per_side=5.0,
                slippage_bps_per_side=2.0,
            )
            self.assertEqual(result["signal_count"], 0)
            return {"fake": "model"}, fake_metrics

        module._original_run_intraday_training = fake_run_intraday_training
        config = {
            "training": {
                "probability_threshold": 0.55,
                "cost_scenarios": [
                    {
                        "name": "base",
                        "fee_bps_per_side": 5.0,
                        "slippage_bps_per_side": 2.0,
                    }
                ],
            }
        }

        model, metrics = module.run_intraday_training_with_threshold_diagnostics(
            items,
            config=config,
            dataset_fingerprint="dataset-sha",
            generated_at_utc="2026-09-15T00:00:00Z",
        )

        self.assertEqual(model, {"fake": "model"})
        self.assertEqual(metrics["model_quality_gate"], configured_gate)
        diagnostics = metrics["threshold_diagnostics_v0_1"]
        self.assertEqual(diagnostics["configured_threshold"], 0.55)
        self.assertIs(diagnostics["diagnostic_only"], True)
        self.assertIs(diagnostics["quality_gate_changed"], False)
        self.assertEqual(len(diagnostics["folds"]), 1)
        rows = {
            row["threshold"]: row
            for row in diagnostics["folds"][0]["rows"]
        }
        self.assertEqual(rows[0.55]["cost_scenarios"]["base"]["signal_count"], 0)
        self.assertEqual(rows[0.50]["cost_scenarios"]["base"]["signal_count"], 3)
        self.assertIs(detailed_training._signal_diagnostics, original_signal_diagnostics)


if __name__ == "__main__":
    unittest.main()
