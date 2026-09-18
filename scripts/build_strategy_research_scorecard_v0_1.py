from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.strategy_research_scorecard_v0_1 import (
    build_strategy_research_scorecard,
    scorecard_input_from_dict,
    scorecard_policy_from_config,
)


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rank existing Strategy Family Validation evidence for research "
            "review priority only. This command cannot select or execute a strategy."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/strategy_research_scorecard_v0_1.json"),
    )
    args = parser.parse_args()

    try:
        reports = scorecard_input_from_dict(_load(args.input))
        policy = scorecard_policy_from_config(_load(args.config))
        report = build_strategy_research_scorecard(reports, policy=policy)
        code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-strategy-research-scorecard-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "ranking_performed": False,
            "winner_selected": False,
            "execution_selection_performed": False,
            "authority": {
                "research_evidence_only": True,
                "research_ranking_authorized": True,
                "ranking_is_trade_recommendation": False,
                "winner_selection_authorized": False,
                "automatic_strategy_selection_authorized": False,
                "strategy_registry_mutation_authorized": False,
                "position_sizing_authorized": False,
                "paper_execution_authorized": False,
                "private_exchange_api_authorized": False,
                "holdout_access_authorized": False,
                "real_money_order_authorized": False,
                "live_real_trading_authorized": False
            }
        }
        code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
