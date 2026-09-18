from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.cycle_v0_1 import paper_cycle_policy_from_config
from crypto_autopilot.paper.execution_v0_1 import paper_execution_policy_from_config
from crypto_autopilot.paper.resume_v0_1 import (
    paper_loop_resume_input_from_dict,
    paper_loop_resume_policy_from_config,
    resume_paper_loop,
)
from crypto_autopilot.portfolio.admission_v0_1 import portfolio_policy_from_config


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one Paper Loop Checkpoint V0.1 and prepare the next manual "
            "Paper Cycle without broker submission, lifecycle simulation or persistence."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--confirm-checkpoint-id", required=True)
    parser.add_argument(
        "--resume-config",
        type=Path,
        default=Path("config/paper_loop_resume_v0_1.json"),
    )
    parser.add_argument(
        "--cycle-config",
        type=Path,
        default=Path("config/paper_cycle_orchestrator_v0_1.json"),
    )
    parser.add_argument(
        "--portfolio-config",
        type=Path,
        default=Path("config/portfolio_admission_v0_1.json"),
    )
    parser.add_argument(
        "--paper-config",
        type=Path,
        default=Path("config/paper_execution_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        resume_policy = paper_loop_resume_policy_from_config(
            _load_json(arguments.resume_config)
        )
        cycle_policy = paper_cycle_policy_from_config(
            _load_json(arguments.cycle_config)
        )
        portfolio_policy = portfolio_policy_from_config(
            _load_json(arguments.portfolio_config)
        )
        execution_policy = paper_execution_policy_from_config(
            _load_json(arguments.paper_config)
        )
        checkpoint_report, candidates = paper_loop_resume_input_from_dict(
            _load_json(arguments.input)
        )
        report = resume_paper_loop(
            checkpoint_report=checkpoint_report,
            confirmation_checkpoint_id=arguments.confirm_checkpoint_id,
            candidate_inputs=candidates,
            resume_policy=resume_policy,
            portfolio_policy=portfolio_policy,
            execution_policy=execution_policy,
            cycle_policy=cycle_policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-loop-resume-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "provider_requests_performed": 0,
            "broker_submissions_performed": 0,
            "lifecycle_simulations_performed": 0,
            "persistent_state_writes_performed": 0,
            "authority": {
                "explicit_manual_cycle_resume_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_state_write_authorized": False,
                "automatic_cycle_authorized": False,
                "automatic_submission_authorized": False,
                "scheduled_execution_authorized": False,
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
