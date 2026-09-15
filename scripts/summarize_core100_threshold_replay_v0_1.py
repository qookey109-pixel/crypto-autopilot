#!/usr/bin/env python3
"""Summarize a completed Core100 threshold replay without touching data sources."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from crypto_autopilot.training.threshold_diagnostics import summarize_thresholds_across_folds


EXPECTED_SCHEMA = "qookey-core100-threshold-sweep-replay-v0.1"


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("schema") != EXPECTED_SCHEMA or report.get("status") != "PASS":
        raise ValueError("unsupported Core100 threshold replay report")
    diagnostics = report.get("threshold_diagnostics_v0_1")
    if not isinstance(diagnostics, dict) or diagnostics.get("status") != "PASS":
        raise ValueError("threshold replay report is missing completed diagnostics")
    folds = diagnostics.get("folds")
    if not isinstance(folds, list) or not folds:
        raise ValueError("threshold replay report is missing fold diagnostics")

    cross_fold = summarize_thresholds_across_folds(folds, scenario_name="base")
    return {
        "schema": "qookey-core100-threshold-sweep-summary-v0.1",
        "status": "PASS",
        "source_training_run_id": report.get("source_training_run_id"),
        "source_dataset_fingerprint": report.get("source_dataset_fingerprint"),
        "dataset_partition_objects": report.get("dataset_partition_objects"),
        "dataset_rows": report.get("dataset_rows"),
        "example_count": report.get("example_count"),
        "configured_threshold": diagnostics.get("configured_threshold"),
        "model_quality_gate": report.get("model_quality_gate"),
        "cross_fold_summary": cross_fold,
        "conclusion": (
            "NO_THRESHOLD_IN_0_50_TO_0_55_SUPPORTED_ACROSS_ALL_FOLDS"
            if not cross_fold["supported_thresholds"]
            else "ONE_OR_MORE_THRESHOLDS_REQUIRE_SEPARATE_EVALUATION"
        ),
        "diagnostic_only": True,
        "threshold_changed": False,
        "quality_gate_changed": False,
        "r2_writes_performed": bool(report.get("r2_writes_performed")),
        "provider_requests_performed": int(report.get("provider_requests_performed", 0)),
        "holdout_accessed": bool(report.get("holdout_accessed")),
        "training_publication_performed": bool(
            report.get("training_publication_performed")
        ),
        "automatic_model_promotion_authorized": False,
        "formal_trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = summarize(payload)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
