from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    paper_lifecycle_batch_input_from_dict,
    paper_lifecycle_batch_policy_from_config,
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.lifecycle_v0_1 import lifecycle_policy_from_config


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Explicitly simulate the complete accepted Paper Submission Session "
            "through Paper Lifecycle V0.1 using caller-supplied normalized bars."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--confirm-session-id", required=True)
    parser.add_argument(
        "--batch-config",
        type=Path,
        default=Path("config/paper_lifecycle_batch_v0_1.json"),
    )
    parser.add_argument(
        "--lifecycle-config",
        type=Path,
        default=Path("config/paper_fill_lifecycle_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        batch_policy = paper_lifecycle_batch_policy_from_config(
            _load_json(arguments.batch_config)
        )
        lifecycle_policy = lifecycle_policy_from_config(
            _load_json(arguments.lifecycle_config)
        )
        session_report, lifecycle_inputs = paper_lifecycle_batch_input_from_dict(
            _load_json(arguments.input)
        )
        report = simulate_paper_lifecycle_batch(
            session_report=session_report,
            confirmation_session_id=arguments.confirm_session_id,
            lifecycle_inputs=lifecycle_inputs,
            batch_policy=batch_policy,
            lifecycle_policy=lifecycle_policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-lifecycle-batch-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "provider_requests_performed": 0,
            "persistent_state_writes_performed": 0,
            "authority": {
                "explicit_paper_lifecycle_simulation_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "automatic_lifecycle_simulation_authorized": False,
                "scheduled_lifecycle_simulation_authorized": False,
                "persistent_state_write_authorized": False,
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
