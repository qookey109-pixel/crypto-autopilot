from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.execution_v0_1 import paper_execution_policy_from_config
from crypto_autopilot.paper.session_v0_1 import (
    paper_submission_session_policy_from_config,
    submit_paper_cycle_session,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Explicitly submit one fully-ready Paper Cycle V0.1 report to a new "
            "in-memory Repository Paper Broker. Exact cycle-id confirmation is required."
        )
    )
    parser.add_argument("--cycle-report", type=Path, required=True)
    parser.add_argument("--confirm-cycle-id", required=True)
    parser.add_argument(
        "--session-config",
        type=Path,
        default=Path("config/paper_submission_session_v0_1.json"),
    )
    parser.add_argument(
        "--paper-config",
        type=Path,
        default=Path("config/paper_execution_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        session_policy = paper_submission_session_policy_from_config(
            _load_json(arguments.session_config)
        )
        execution_policy = paper_execution_policy_from_config(
            _load_json(arguments.paper_config)
        )
        cycle_report = _load_json(arguments.cycle_report)
        report = submit_paper_cycle_session(
            cycle_report=cycle_report,
            confirmation_cycle_id=arguments.confirm_cycle_id,
            broker=PaperBroker(),
            session_policy=session_policy,
            execution_policy=execution_policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-submission-session-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "new_submission_count": 0,
            "replayed_submission_count": 0,
            "lifecycle_simulations_performed": 0,
            "persistent_state_writes_performed": 0,
            "authority": {
                "explicit_in_memory_paper_submission_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "automatic_submission_authorized": False,
                "scheduled_submission_authorized": False,
                "persistent_broker_state_authorized": False,
                "lifecycle_simulation_authorized": False,
                "short_paper_execution_authorized": False,
                "formal_trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        exit_code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
