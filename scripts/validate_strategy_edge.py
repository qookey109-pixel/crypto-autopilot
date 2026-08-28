from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.strategy_edge_validation import (
    EdgeValidationError,
    edge_input_from_dict,
    policy_from_dict,
    validate_strategy_edge,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EdgeValidationError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate aligned strategy-return evidence without provider/R2 access."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/strategy_edge_validation_v0_1.json"),
    )
    arguments = parser.parse_args()
    try:
        evidence = edge_input_from_dict(_load_json(arguments.input))
        policy = policy_from_dict(_load_json(arguments.config))
        report = validate_strategy_edge(evidence, policy)
    except (EdgeValidationError, json.JSONDecodeError, OSError) as error:
        report = {
            "schema": "qookey-strategy-edge-validation-report-v0.1",
            "verdict": "REJECT",
            "reasons": [f"input_or_policy_invalid:{error}"],
            "authority": {
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "promotion_authority": 0,
                "trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
                "v0_10_production_critical_path_mutated": False,
            },
        }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
