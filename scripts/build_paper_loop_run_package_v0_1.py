from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.integrity_v0_1 import (
    paper_loop_integrity_policy_from_config,
)
from crypto_autopilot.paper.run_package_v0_1 import (
    build_paper_loop_run_package,
    paper_loop_run_package_input_from_dict,
    paper_loop_run_package_policy_from_config,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create one portable self-verifying Paper Loop transcript package "
            "without persistence, provider access or execution authority."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--confirm-integrity-id", required=True)
    parser.add_argument(
        "--package-config",
        type=Path,
        default=Path("config/paper_loop_run_package_v0_1.json"),
    )
    parser.add_argument(
        "--integrity-config",
        type=Path,
        default=Path("config/paper_loop_integrity_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        package_policy = paper_loop_run_package_policy_from_config(
            _load_json(arguments.package_config)
        )
        integrity_policy = paper_loop_integrity_policy_from_config(
            _load_json(arguments.integrity_config)
        )
        integrity_input, integrity_report = paper_loop_run_package_input_from_dict(
            _load_json(arguments.input)
        )
        report = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=arguments.confirm_integrity_id,
            package_policy=package_policy,
            integrity_policy=integrity_policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-loop-run-package-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "provider_requests_performed": 0,
            "persistent_state_writes_performed": 0,
            "executions_performed": 0,
            "authority": {
                "portable_audit_package_only": True,
                "package_is_execution_authority": False,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_state_write_authorized": False,
                "automatic_execution_authorized": False,
                "automatic_submission_authorized": False,
                "strategy_ranking_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        exit_code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
