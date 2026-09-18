from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.account_v0_1 import (
    paper_account_policy_from_config,
)
from crypto_autopilot.paper.cycle_v0_1 import (
    paper_cycle_input_from_dict,
    paper_cycle_policy_from_config,
    prepare_paper_cycle,
)
from crypto_autopilot.paper.execution_v0_1 import (
    paper_execution_policy_from_config,
)
from crypto_autopilot.portfolio.admission_v0_1 import (
    portfolio_policy_from_config,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare one explicit deterministic paper cycle through account state, "
            "portfolio admission and paper-intent readiness without broker submission."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--cycle-config",
        type=Path,
        default=Path("config/paper_cycle_orchestrator_v0_1.json"),
    )
    parser.add_argument(
        "--account-config",
        type=Path,
        default=Path("config/paper_account_state_v0_1.json"),
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
        cycle_policy = paper_cycle_policy_from_config(
            _load_json(arguments.cycle_config)
        )
        account_policy = paper_account_policy_from_config(
            _load_json(arguments.account_config)
        )
        portfolio_policy = portfolio_policy_from_config(
            _load_json(arguments.portfolio_config)
        )
        execution_policy = paper_execution_policy_from_config(
            _load_json(arguments.paper_config)
        )
        account_input, candidates = paper_cycle_input_from_dict(
            _load_json(arguments.input)
        )
        report = prepare_paper_cycle(
            account_input=account_input,
            candidate_inputs=candidates,
            account_policy=account_policy,
            portfolio_policy=portfolio_policy,
            execution_policy=execution_policy,
            cycle_policy=cycle_policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-cycle-report-v0.1",
            "state": "REJECT",
            "reasons": [f"input_or_policy_invalid:{error}"],
            "broker_submissions_performed": 0,
            "lifecycle_simulations_performed": 0,
            "persistent_state_writes_performed": 0,
            "explicit_submission_required": True,
            "explicit_submission_allowed": False,
            "authority": {
                "manual_cycle_preparation_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_state_written": False,
                "strategy_ranking_authorized": False,
                "automatic_subset_selection_authorized": False,
                "automatic_broker_submission_authorized": False,
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
