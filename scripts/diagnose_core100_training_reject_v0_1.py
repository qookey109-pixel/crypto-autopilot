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


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _number(obj: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def diagnose(metrics: dict[str, Any]) -> dict[str, Any]:
    fold_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []

    seen_folds: set[tuple[Any, ...]] = set()
    seen_costs: set[tuple[Any, ...]] = set()

    for obj in _iter_dicts(metrics):
        fold = obj.get("fold", obj.get("fold_id", obj.get("name")))
        model_log_loss = _number(obj, "model_log_loss", "log_loss")
        naive_log_loss = _number(obj, "naive_log_loss", "baseline_log_loss")
        if model_log_loss is not None and naive_log_loss is not None:
            delta = model_log_loss - naive_log_loss
            key = (fold, model_log_loss, naive_log_loss)
            if key not in seen_folds:
                seen_folds.add(key)
                fold_rows.append(
                    {
                        "fold": fold,
                        "model_log_loss": model_log_loss,
                        "naive_log_loss": naive_log_loss,
                        "delta_vs_naive": delta,
                        "beats_naive": delta < 0,
                    }
                )

        average_return = _number(
            obj,
            "average_return",
            "avg_return",
            "mean_return",
            "net_average_return",
        )
        if average_return is not None:
            cost = _number(
                obj,
                "cost_bps",
                "transaction_cost_bps",
                "fee_bps",
                "base_cost_bps",
            )
            scenario = obj.get("scenario", obj.get("cost_scenario", obj.get("name")))
            if cost is not None or scenario is not None:
                key = (scenario, cost, average_return)
                if key not in seen_costs:
                    seen_costs.add(key)
                    cost_rows.append(
                        {
                            "scenario": scenario,
                            "cost_bps": cost,
                            "average_return": average_return,
                            "positive": average_return > 0,
                        }
                    )

    fold_rows.sort(key=lambda row: row["delta_vs_naive"], reverse=True)
    cost_rows.sort(key=lambda row: row["average_return"])

    failing_folds = [row for row in fold_rows if not row["beats_naive"]]
    failing_costs = [row for row in cost_rows if not row["positive"]]

    return {
        "schema": "qookey-core100-training-reject-diagnosis-v0.1",
        "fold_metrics_found": len(fold_rows),
        "failing_fold_count": len(failing_folds),
        "cost_scenarios_found": len(cost_rows),
        "failing_cost_scenario_count": len(failing_costs),
        "worst_folds": fold_rows[:10],
        "worst_cost_scenarios": cost_rows[:10],
        "failing_folds": failing_folds,
        "failing_cost_scenarios": failing_costs,
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
