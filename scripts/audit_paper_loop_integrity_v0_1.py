from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.integrity_v0_1 import (
    audit_paper_loop_integrity,
    paper_loop_integrity_input_from_dict,
    paper_loop_integrity_policy_from_config,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit two or more complete Paper Loop rounds for deterministic lineage, "
            "checkpoint continuity and replay integrity without executing them."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/paper_loop_integrity_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        policy = paper_loop_integrity_policy_from_config(
            _load_json(arguments.config)
        )
        start, terminal, rounds = paper_loop_integrity_input_from_dict(
            _load_json(arguments.input)
        )
        report = audit_paper_loop_integrity(
            expected_start_checkpoint_id=start,
            expected_terminal_checkpoint_id=terminal,
            rounds=rounds,
            policy=policy,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-paper-loop-integrity-report-v0.1",
            "state": "REJECT",
            "reason": f"input_or_policy_invalid:{error}",
            "provider_requests_performed": 0,
            "persistent_state_writes_performed": 0,
            "executions_performed": 0,
            "authority": {
                "audit_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "persistent_state_write_authorized": False,
                "automatic_execution_authorized": False,
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
