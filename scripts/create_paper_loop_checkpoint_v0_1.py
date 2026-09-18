from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.checkpoint_v0_1 import (
    create_paper_loop_checkpoint,
    paper_loop_checkpoint_policy_from_config,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a portable deterministic Paper Loop checkpoint from one "
            "successful Paper Account Advance report without persistent storage."
        )
    )
    parser.add_argument("--advance-report", type=Path, required=True)
    parser.add_argument("--confirm-advance-id", required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/paper_loop_checkpoint_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        policy = paper_loop_checkpoint_policy_from_config(
            _load_json(arguments.config)
        )
        report = create_paper_loop_checkpoint(
            account_advance_report=_load_json(arguments.advance_report),
            confirmation_advance_id=arguments.confirm_advance_id,
            policy=policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-loop-checkpoint-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "next_cycle_allowed": False,
            "provider_requests_performed": 0,
            "persistent_state_writes_performed": 0,
            "authority": {
                "portable_handoff_only": True,
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
