import json
import subprocess
import sys
from pathlib import Path


def test_diagnose_core100_training_reject_reports_failing_fold_and_cost(tmp_path: Path) -> None:
    metrics = {
        "folds": [
            {"fold": "fold-1", "model_log_loss": 0.61, "naive_log_loss": 0.60},
            {"fold": "fold-2", "model_log_loss": 0.55, "naive_log_loss": 0.60},
        ],
        "cost_scenarios": [
            {"scenario": "base-1", "cost_bps": 5, "average_return": -0.001},
            {"scenario": "base-2", "cost_bps": 2, "average_return": 0.002},
        ],
    }
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
    assert diagnosis["fold_metrics_found"] == 2
    assert diagnosis["failing_fold_count"] == 1
    assert diagnosis["failing_folds"][0]["fold"] == "fold-1"
    assert diagnosis["cost_scenarios_found"] == 2
    assert diagnosis["failing_cost_scenario_count"] == 1
    assert diagnosis["failing_cost_scenarios"][0]["scenario"] == "base-1"
    assert diagnosis["diagnostic_only"] is True
    assert diagnosis["automatic_model_promotion_authorized"] is False
    assert diagnosis["formal_trade_plan_authorized"] is False
    assert diagnosis["real_money_order_authorized"] is False
    assert diagnosis["live_trading_authorized"] is False
