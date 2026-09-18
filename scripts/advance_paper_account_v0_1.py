from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.account_advance_v0_1 import (
    advance_paper_account,
    paper_account_advance_input_from_dict,
    paper_account_advance_policy_from_config,
)
from crypto_autopilot.paper.account_v0_1 import paper_account_policy_from_config


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Advance immutable Paper Account V0.1 state by replacing/adding latest "
            "lifecycle records from one complete Paper Lifecycle Batch report."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--confirm-batch-id", required=True)
    parser.add_argument(
        "--advance-config",
        type=Path,
        default=Path("config/paper_account_advance_v0_1.json"),
    )
    parser.add_argument(
        "--account-config",
        type=Path,
        default=Path("config/paper_account_state_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        advance_policy = paper_account_advance_policy_from_config(
            _load_json(arguments.advance_config)
        )
        account_policy = paper_account_policy_from_config(
            _load_json(arguments.account_config)
        )
        previous, batch, next_marks = paper_account_advance_input_from_dict(
            _load_json(arguments.input)
        )
        report = advance_paper_account(
            previous_account_input=previous,
            lifecycle_batch_report=batch,
            confirmation_batch_id=arguments.confirm_batch_id,
            next_marks=next_marks,
            advance_policy=advance_policy,
            account_policy=account_policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-account-advance-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "portfolio_existing_exposures": [],
            "portfolio_capacity_exported": False,
            "provider_requests_performed": 0,
            "persistent_state_writes_performed": 0,
            "authority": {
                "explicit_account_rematerialization_only": True,
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
