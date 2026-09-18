from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.lifecycle_v0_1 import (
    build_paper_lifecycle_plan,
    lifecycle_evidence,
    lifecycle_input_from_dict,
    lifecycle_policy_from_config,
    simulate_paper_lifecycle,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate deterministic paper fills and LONG stop/target lifecycle "
            "from existing Paper Execution evidence and normalized liquidity bars."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/paper_fill_lifecycle_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        policy = lifecycle_policy_from_config(_load_json(arguments.config))
        decision, receipt, target_price, bars = lifecycle_input_from_dict(
            _load_json(arguments.input)
        )
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=target_price,
        )
        result = simulate_paper_lifecycle(
            plan=plan,
            bars=bars,
            policy=policy,
        )
        report = lifecycle_evidence(plan=plan, result=result, policy=policy)
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-fill-lifecycle-report-v0.1",
            "status": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "authority": {
                "paper_simulation_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_broker_state_written": False,
                "automatic_submission_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        exit_code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
