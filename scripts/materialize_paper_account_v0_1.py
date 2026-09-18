from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.paper.account_v0_1 import (
    materialize_paper_account,
    paper_account_evidence,
    paper_account_input_from_dict,
    paper_account_policy_from_config,
    portfolio_exposures_from_account,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild immutable paper account/position state from latest lifecycle "
            "evidence and explicit marks without provider, R2 or persistent-state access."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/paper_account_state_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        policy = paper_account_policy_from_config(_load_json(arguments.config))
        initial, records, marks = paper_account_input_from_dict(
            _load_json(arguments.input)
        )
        snapshot = materialize_paper_account(
            initial_equity_usd=initial,
            records=records,
            marks=marks,
            policy=policy,
        )
        exposures = (
            portfolio_exposures_from_account(snapshot, policy=policy)
            if snapshot.status == "ACCOUNT_ACTIVE"
            else ()
        )
        report = {
            "schema": "qookey-paper-account-materialization-run-v0.1",
            "account": paper_account_evidence(snapshot, policy),
            "portfolio_existing_exposures": [asdict(item) for item in exposures],
            "portfolio_capacity_exported": snapshot.status == "ACCOUNT_ACTIVE",
            "authority": {
                "paper_state_materialization_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_state_written": False,
                "automatic_submission_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-account-materialization-run-v0.1",
            "status": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "portfolio_existing_exposures": [],
            "portfolio_capacity_exported": False,
            "authority": {
                "paper_state_materialization_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_state_written": False,
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
