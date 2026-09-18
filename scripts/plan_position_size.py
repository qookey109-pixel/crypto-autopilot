from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.risk import (
    plan_position_size,
    position_sizing_policy_from_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan bounded LONG/SHORT research position size from an upstream stop "
            "without provider, R2 or order access."
        )
    )
    parser.add_argument("--direction", choices=("LONG", "SHORT"), required=True)
    parser.add_argument("--equity-usd", type=float, required=True)
    parser.add_argument("--entry-price", type=float, required=True)
    parser.add_argument("--stop-price", type=float, required=True)
    parser.add_argument("--realized-daily-r", type=float, default=0.0)
    parser.add_argument("--new-positions-today", type=int, default=0)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/risk_position_sizing_v0_1.json"),
    )
    arguments = parser.parse_args()

    try:
        payload = json.loads(arguments.config.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("config must contain a JSON object")
        policy = position_sizing_policy_from_config(payload)
        plan = plan_position_size(
            direction=arguments.direction,
            equity_usd=arguments.equity_usd,
            entry_price=arguments.entry_price,
            stop_price=arguments.stop_price,
            realized_daily_r=arguments.realized_daily_r,
            new_positions_today=arguments.new_positions_today,
            policy=policy,
        )
        report = {
            "schema": "qookey-risk-position-sizing-report-v0.1",
            "plan": asdict(plan),
            "authority": {
                "research_sizing_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "paper_execution_authorized": False,
                "short_execution_authorized": False,
                "trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False
            }
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "schema": "qookey-risk-position-sizing-report-v0.1",
            "plan": {
                "status": "NO_TRADE",
                "reason": f"input_or_policy_invalid:{error}"
            },
            "authority": {
                "research_sizing_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "paper_execution_authorized": False,
                "short_execution_authorized": False,
                "trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False
            }
        }

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["plan"]["status"] == "SIZING_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
