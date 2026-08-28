from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from crypto_autopilot.strategy_edge_validation import edge_input_from_dict
from crypto_autopilot.strategy_research_loop import (
    StrategyResearchLoopError,
    audit_paper_performance,
    build_candidate_registry,
    compose_research_evidence,
    paper_ledger_from_dict,
    policy_from_config,
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyResearchLoopError(f"{path} must contain one JSON object")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the synthetic-only Strategy Research Loop V0.1")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/strategy_research_loop_v0_1.json"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("registry")
    audit = subparsers.add_parser("audit")
    audit.add_argument("--ledger", required=True, type=Path)
    compose = subparsers.add_parser("compose")
    compose.add_argument("--edge-input", required=True, type=Path)
    compose.add_argument("--edge-report", required=True, type=Path)
    compose.add_argument("--ledger", required=True, type=Path)
    return parser


def main() -> int:
    try:
        arguments = _parser().parse_args()
        config = _read_json(arguments.config)
        registry = build_candidate_registry(config)
        if arguments.command == "registry":
            report = registry.report()
            status = 0
        else:
            ledger = paper_ledger_from_dict(_read_json(arguments.ledger))
            audit = audit_paper_performance(ledger, policy_from_config(config))
            if arguments.command == "audit":
                report = audit
                status = 0 if audit["state"] == "ACCEPTABLE_FOR_CONTINUED_PAPER_RESEARCH" else 2
            else:
                edge_input = edge_input_from_dict(_read_json(arguments.edge_input))
                edge_report = _read_json(arguments.edge_report)
                report = compose_research_evidence(
                    registry=registry,
                    edge_input=edge_input,
                    edge_report=edge_report,
                    paper_audit=audit,
                )
                status = 0 if report["state"] == "EVIDENCE_READY_FOR_HUMAN_REVIEW" else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        report = {
            "schema": "qookey-strategy-research-loop-error-v0.1",
            "state": "REJECT",
            "reasons": [f"invalid_or_unauthorized_input:{error}"],
            "authority": {
                "model_promotion_authority": 0,
                "trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        status = 2
    json.dump(report, sys.stdout, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write("\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
