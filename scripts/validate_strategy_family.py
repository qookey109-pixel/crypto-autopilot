from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.strategy_family_validation import (
    StrategyFamilyValidationError,
    family_validation_input_from_dict,
    policy_from_config,
    validate_strategy_family,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyFamilyValidationError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate existing Strategy Edge Validation reports into "
            "family-level generalization review evidence without provider/R2 access."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/strategy_family_validation_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        family, receipts = family_validation_input_from_dict(
            _load_json(arguments.input)
        )
        policy = policy_from_config(_load_json(arguments.config))
        report = validate_strategy_family(family, receipts, policy)
    except (StrategyFamilyValidationError, json.JSONDecodeError, OSError) as error:
        report = {
            "schema": "qookey-strategy-family-validation-report-v0.1",
            "state": "REJECT",
            "reasons": [f"input_or_policy_invalid:{error}"],
            "authority": {
                "research_evidence_only": True,
                "strategy_edge_claimed": False,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "promotion_authority": 0,
                "position_sizing_authorized": False,
                "paper_execution_authorized": False,
                "trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["state"] == "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
