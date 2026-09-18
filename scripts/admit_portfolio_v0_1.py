from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.portfolio.admission_v0_1 import (
    admit_portfolio,
    portfolio_admission_input_from_dict,
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
            "Evaluate one explicit multi-strategy basket against Portfolio "
            "Admission V0.1 without provider, R2, broker or live-trading access."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/portfolio_admission_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        policy = portfolio_policy_from_config(_load_json(arguments.config))
        equity_usd, proposals, existing = portfolio_admission_input_from_dict(
            _load_json(arguments.input)
        )
        report = admit_portfolio(
            equity_usd=equity_usd,
            proposals=proposals,
            existing_exposures=existing,
            policy=policy,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-portfolio-admission-report-v0.1",
            "state": "PORTFOLIO_REVIEW_REQUIRED",
            "reasons": [f"input_or_policy_invalid:{error}"],
            "admitted_proposal_ids": [],
            "rejected_proposal_ids": [],
            "ranking_performed": False,
            "subset_selection_performed": False,
            "authority": {
                "research_paper_admission_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "strategy_ranking_authorized": False,
                "automatic_subset_selection_authorized": False,
                "paper_execution_authorized": False,
                "short_paper_execution_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["state"] == "PORTFOLIO_ADMITTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
