from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.execution_v0_1 import (
    paper_execution_evidence,
    paper_execution_policy_from_config,
    prepare_paper_execution,
    submit_paper_execution,
)
from crypto_autopilot.risk import plan_position_size, position_sizing_policy_from_config


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a local in-memory Paper Execution V0.1 integration from an "
            "existing family-validation report and explicit risk inputs."
        )
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy-family", required=True)
    parser.add_argument("--family-validation-report", type=Path, required=True)
    parser.add_argument("--direction", choices=("LONG", "SHORT"), required=True)
    parser.add_argument("--equity-usd", type=float, required=True)
    parser.add_argument("--entry-price", type=float, required=True)
    parser.add_argument("--stop-price", type=float, required=True)
    parser.add_argument("--as-of-ms", type=int, required=True)
    parser.add_argument("--realized-daily-r", type=float, default=0.0)
    parser.add_argument("--new-positions-today", type=int, default=0)
    parser.add_argument(
        "--risk-config",
        type=Path,
        default=Path("config/risk_position_sizing_v0_1.json"),
    )
    parser.add_argument(
        "--paper-config",
        type=Path,
        default=Path("config/paper_execution_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        risk_policy = position_sizing_policy_from_config(
            _load_json(arguments.risk_config)
        )
        paper_policy = paper_execution_policy_from_config(
            _load_json(arguments.paper_config)
        )
        family_report = _load_json(arguments.family_validation_report)

        sizing = plan_position_size(
            direction=arguments.direction,
            equity_usd=arguments.equity_usd,
            entry_price=arguments.entry_price,
            stop_price=arguments.stop_price,
            realized_daily_r=arguments.realized_daily_r,
            new_positions_today=arguments.new_positions_today,
            policy=risk_policy,
        )

        decision = prepare_paper_execution(
            symbol=arguments.symbol,
            strategy_family=arguments.strategy_family,
            family_validation_report=family_report,
            as_of_ms=arguments.as_of_ms,
            sizing_plan=sizing,
            policy=paper_policy,
        )

        receipt = None
        if decision.status == "READY_FOR_PAPER_BROKER":
            receipt = submit_paper_execution(
                decision,
                PaperBroker(),
                policy=paper_policy,
            )

        report = {
            "schema": "qookey-paper-execution-integration-run-v0.1",
            "mode": "LOCAL_IN_MEMORY_PAPER_ONLY",
            "position_sizing": asdict(sizing),
            "paper_execution": paper_execution_evidence(decision, receipt),
            "authority": {
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_broker_state_written": False,
                "automatic_submission_authorized": False,
                "short_paper_execution_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-execution-integration-run-v0.1",
            "mode": "LOCAL_IN_MEMORY_PAPER_ONLY",
            "status": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "authority": {
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_broker_state_written": False,
                "automatic_submission_authorized": False,
                "short_paper_execution_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    if "paper_execution" not in report:
        return 2
    decision = report["paper_execution"]["decision"]
    return 0 if decision["status"] == "READY_FOR_PAPER_BROKER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
