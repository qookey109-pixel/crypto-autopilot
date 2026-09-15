#!/usr/bin/env python3
"""Diagnose a Core100 training quality-gate rejection from metrics.json.

This is a read-only research diagnostic. It does not promote models or authorize
trade plans, real-money orders, source switching, or live trading.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "binance-usdm-intraday-research-metrics-v0.1"


def _number(value: Any, *, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def _integer(value: Any, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    return value


def diagnose(metrics: dict[str, Any]) -> dict[str, Any]:
    if metrics.get("schema") != EXPECTED_SCHEMA or metrics.get("status") != "PASS":
        raise ValueError("unsupported Core100 training metrics payload")

    folds = metrics.get("walk_forward_folds")
    if not isinstance(folds, list):
        raise ValueError("walk_forward_folds must be a list")

    fold_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []

    for fold in folds:
        if not isinstance(fold, dict):
            raise ValueError("walk_forward_folds entries must be objects")
        name = str(fold.get("name") or "")
        status = str(fold.get("status") or "")
        if status != "PASS":
            fold_rows.append(
                {
                    "fold": name,
                    "status": status or "UNKNOWN",
                    "train_samples": fold.get("train_samples"),
                    "test_samples": fold.get("test_samples"),
                    "beats_naive": False,
                    "delta_vs_naive": None,
                }
            )
            continue

        model_metrics = fold.get("metrics")
        baseline_metrics = fold.get("naive_train_prevalence_baseline")
        if not isinstance(model_metrics, dict) or not isinstance(baseline_metrics, dict):
            raise ValueError(f"fold {name!r} is missing probability metrics")
        model_log_loss = _number(model_metrics.get("log_loss"), field="metrics.log_loss")
        naive_log_loss = _number(
            baseline_metrics.get("log_loss"), field="naive_train_prevalence_baseline.log_loss"
        )
        delta = model_log_loss - naive_log_loss
        beats_naive = bool(fold.get("beats_naive_log_loss"))
        fold_rows.append(
            {
                "fold": name,
                "status": status,
                "train_samples": fold.get("train_samples"),
                "test_samples": fold.get("test_samples"),
                "model_log_loss": model_log_loss,
                "naive_log_loss": naive_log_loss,
                "delta_vs_naive": delta,
                "beats_naive": beats_naive,
            }
        )

        scenarios = fold.get("cost_scenarios")
        if not isinstance(scenarios, dict):
            raise ValueError(f"fold {name!r} is missing cost_scenarios")
        for scenario_name, scenario in scenarios.items():
            if not isinstance(scenario, dict):
                raise ValueError(f"fold {name!r} cost scenario {scenario_name!r} must be an object")
            average_net_return = _number(
                scenario.get("average_net_return"),
                field=f"cost_scenarios.{scenario_name}.average_net_return",
            )
            signal_count = _integer(
                scenario.get("signal_count"),
                field=f"cost_scenarios.{scenario_name}.signal_count",
            )
            cost_rows.append(
                {
                    "fold": name,
                    "scenario": str(scenario_name),
                    "signal_count": signal_count,
                    "average_net_return": average_net_return,
                    "positive": average_net_return > 0.0,
                    "diagnostic_growth": scenario.get("diagnostic_growth"),
                    "maximum_drawdown": scenario.get("maximum_drawdown"),
                    "maximum_symbol_concentration": scenario.get(
                        "maximum_symbol_concentration"
                    ),
                }
            )

    def fold_sort_key(row: dict[str, Any]) -> float:
        delta = row.get("delta_vs_naive")
        return float("inf") if delta is None else float(delta)

    fold_rows.sort(key=fold_sort_key, reverse=True)
    cost_rows.sort(key=lambda row: float(row["average_net_return"]))

    failing_folds = [row for row in fold_rows if not row["beats_naive"]]
    base_cost_rows = [row for row in cost_rows if row["scenario"] == "base"]
    failing_base_costs = [row for row in base_cost_rows if not row["positive"]]
    zero_signal_base_costs = [row for row in base_cost_rows if row["signal_count"] == 0]

    gate = metrics.get("model_quality_gate")
    if not isinstance(gate, dict):
        raise ValueError("model_quality_gate must be an object")

    return {
        "schema": "qookey-core100-training-reject-diagnosis-v0.1",
        "source_metrics_schema": metrics["schema"],
        "source_dataset_fingerprint": metrics.get("dataset_fingerprint"),
        "source_model_quality_gate": gate,
        "fold_metrics_found": len(fold_rows),
        "failing_fold_count": len(failing_folds),
        "base_cost_scenarios_found": len(base_cost_rows),
        "failing_base_cost_scenario_count": len(failing_base_costs),
        "zero_signal_base_cost_scenario_count": len(zero_signal_base_costs),
        "worst_folds": fold_rows[:10],
        "worst_base_cost_scenarios": base_cost_rows[:10],
        "failing_folds": failing_folds,
        "failing_base_cost_scenarios": failing_base_costs,
        "zero_signal_base_cost_scenarios": zero_signal_base_costs,
        "diagnostic_only": True,
        "automatic_model_promotion_authorized": False,
        "formal_trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("metrics", type=Path, help="Path to published metrics.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    metrics = json.loads(args.metrics.read_text())
    result = diagnose(metrics)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
