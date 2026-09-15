from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_core100_threshold_replay_v0_1.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("summarize_core100_threshold_replay_v0_1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fold(name: str, *, at_050: tuple[int, float], at_051: tuple[int, float]):
    def row(threshold: float, values: tuple[int, float]):
        count, average = values
        return {
            "threshold": threshold,
            "cost_scenarios": {
                "base": {
                    "signal_count": count,
                    "average_net_return": average,
                    "maximum_drawdown": 0.1 if count else 0.0,
                    "maximum_symbol_concentration": 0.5 if count else 0.0,
                }
            },
        }

    return {
        "name": name,
        "candidate_thresholds": [0.50, 0.51],
        "probability_distribution": {"count": 100},
        "rows": [row(0.50, at_050), row(0.51, at_051)],
    }


class Core100ThresholdReplaySummaryTests(unittest.TestCase):
    def test_summary_refuses_threshold_change_when_no_candidate_passes_all_folds(self) -> None:
        module = _load_module()
        report = {
            "schema": "qookey-core100-threshold-sweep-replay-v0.1",
            "status": "PASS",
            "source_training_run_id": 34918219864,
            "source_dataset_fingerprint": "dataset-sha",
            "dataset_partition_objects": 14274,
            "dataset_rows": 18235427,
            "example_count": 249228,
            "model_quality_gate": {"status": "REJECT"},
            "threshold_diagnostics_v0_1": {
                "status": "PASS",
                "configured_threshold": 0.55,
                "folds": [
                    _fold("fold-1", at_050=(10, -0.01), at_051=(2, -0.02)),
                    _fold("fold-2", at_050=(5, 0.02), at_051=(0, 0.0)),
                ],
            },
            "r2_writes_performed": False,
            "provider_requests_performed": 0,
            "holdout_accessed": False,
            "training_publication_performed": False,
        }

        result = module.summarize(report)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["conclusion"],
            "NO_THRESHOLD_IN_0_50_TO_0_55_SUPPORTED_ACROSS_ALL_FOLDS",
        )
        self.assertEqual(result["cross_fold_summary"]["supported_thresholds"], [])
        self.assertIs(
            result["cross_fold_summary"]["threshold_change_supported"], False
        )
        self.assertIs(result["threshold_changed"], False)
        self.assertIs(result["quality_gate_changed"], False)
        self.assertIs(result["r2_writes_performed"], False)
        self.assertEqual(result["provider_requests_performed"], 0)
        self.assertIs(result["holdout_accessed"], False)
        self.assertIs(result["live_trading_authorized"], False)


if __name__ == "__main__":
    unittest.main()
