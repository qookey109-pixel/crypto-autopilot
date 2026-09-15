#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "strategy_name",
    "summary",
    "timeframes",
    "markets",
    "indicators",
    "entry_rules",
    "exit_rules",
    "risk_rules",
    "claimed_metrics",
    "uncertainties",
    "evidence",
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return value


def validate_analysis(analysis: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in analysis]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    for field in ("strategy_name", "summary"):
        if not isinstance(analysis[field], str) or not analysis[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in (
        "timeframes",
        "markets",
        "entry_rules",
        "exit_rules",
        "risk_rules",
        "uncertainties",
    ):
        require_string_list(analysis[field], field)
    if not isinstance(analysis["indicators"], list):
        raise ValueError("indicators must be a list")
    if not isinstance(analysis["claimed_metrics"], list):
        raise ValueError("claimed_metrics must be a list")
    if not isinstance(analysis["evidence"], list) or not analysis["evidence"]:
        raise ValueError("evidence must be a non-empty list")
    for item in analysis["evidence"]:
        if not isinstance(item, dict):
            raise ValueError("evidence entries must be objects")
        if not isinstance(item.get("claim"), str) or not item["claim"].strip():
            raise ValueError("evidence.claim must be a non-empty string")
        locator = item.get("source_locator")
        if not isinstance(locator, str) or not locator.strip():
            raise ValueError("evidence.source_locator must be a non-empty string")
        if item.get("confidence") not in {"high", "medium", "low"}:
            raise ValueError("evidence.confidence must be high, medium, or low")
    for item in analysis["claimed_metrics"]:
        if not isinstance(item, dict):
            raise ValueError("claimed_metrics entries must be objects")
        locator = item.get("source_locator")
        if not isinstance(locator, str) or not locator.strip():
            raise ValueError("claimed_metrics.source_locator must be a non-empty string")


def build_candidate(analysis: dict[str, Any], *, source: str) -> dict[str, Any]:
    validate_analysis(analysis)
    digest = hashlib.sha256(canonical_json_bytes(analysis)).hexdigest()
    return {
        "schema": "video-strategy-candidate-v0.1",
        "status": "UNVERIFIED_RESEARCH_CANDIDATE",
        "source": source,
        "analysis_sha256": digest,
        "strategy": analysis,
        "verification": {
            "notebooklm_grounded_analysis_received": True,
            "claimed_metrics_verified": False,
            "production_backtest_performed": False,
            "walk_forward_performed": False,
            "strategy_promotion_authorized": False,
        },
        "next_gate": {
            "target": "strategy_research_loop_v0_1",
            "requires_separate_reviewed_authority_for_production_dataset": True,
        },
        "authority": {
            "r2_access_authorized": False,
            "holdout_access_authorized": False,
            "source_switch_authorized": False,
            "automatic_strategy_mutation_authorized": False,
            "automatic_model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate grounded NotebookLM video analysis and materialize a research-only candidate."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    analysis = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(analysis, dict):
        raise ValueError("analysis root must be an object")
    candidate = build_candidate(analysis, source=args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(candidate))
    print(json.dumps(candidate, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
