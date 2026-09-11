#!/usr/bin/env python3
"""Run one bounded public Pionex funding-history capture after authority merge."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path

from crypto_autopilot.history.pionex_funding_history import (
    PionexFundingHistoryRejected,
    collect_bounded_funding_history,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config/pionex_funding_history_v0_1.json"
EXEC_CONFIG = ROOT / "config/pionex_funding_history_execution_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-11-pionex-funding-history-execution-v0-1-authority.json"
PROTOCOL_SHA256 = "9117e707203b35ef9d7420b96033cd339b97c549f03e3cdae2ecece4637b6834"
EXEC_CONFIG_SHA256 = "d2cdafc5900573eb7d9971b7e3d7b9e5e34f50d16a510b56dcd7e0512b5e3315"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stamp(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def require_github_main_dispatch() -> None:
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise PionexFundingHistoryRejected(
            "fresh GitHub main workflow_dispatch attempt 1 required"
        )
    if not (os.environ.get("GITHUB_RUN_ID") or "").isdigit():
        raise PionexFundingHistoryRejected("GitHub run id missing")


def load_authority(now: datetime | None = None) -> tuple[dict, dict]:
    protocol_bytes = PROTOCOL.read_bytes()
    exec_bytes = EXEC_CONFIG.read_bytes()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if digest(protocol_bytes) != PROTOCOL_SHA256:
        raise PionexFundingHistoryRejected("funding protocol bytes changed")
    if digest(exec_bytes) != EXEC_CONFIG_SHA256:
        raise PionexFundingHistoryRejected("funding execution config bytes changed")
    if receipt.get("protocol_config_sha256") != PROTOCOL_SHA256:
        raise PionexFundingHistoryRejected("authority does not bind protocol config")
    if receipt.get("execution_config_sha256") != EXEC_CONFIG_SHA256:
        raise PionexFundingHistoryRejected("authority does not bind execution config")
    if receipt.get("execution_performed_by_this_receipt") is not False:
        raise PionexFundingHistoryRejected("authority receipt cannot claim execution")
    protocol = json.loads(protocol_bytes)
    execution = json.loads(exec_bytes)
    if execution.get("status") != receipt.get("status"):
        raise PionexFundingHistoryRejected("execution config/receipt status mismatch")
    if execution.get("protocol", {}).get("config_sha256") != PROTOCOL_SHA256:
        raise PionexFundingHistoryRejected("execution config does not bind protocol")
    current = now or datetime.now(UTC)
    start = stamp(execution["execution"]["not_before_utc"])
    stop = stamp(execution["execution"]["stop_exclusive_utc"])
    if not start <= current < stop:
        raise PionexFundingHistoryRejected("execution window closed")
    if execution["execution"].get("automatic_retries") != 0:
        raise PionexFundingHistoryRejected("automatic retries changed")
    return protocol, execution


def main() -> int:
    from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = {
        "schema": "pionex-funding-history-run-report-v0.1",
        "status": "FAIL",
        "protocol_config_sha256": PROTOCOL_SHA256,
        "execution_config_sha256": EXEC_CONFIG_SHA256,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "head_ref": os.environ.get("GITHUB_REF"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "api_key_used": False,
        "private_api_used": False,
        "raw_provider_payloads_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "simulation_data_admission_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }

    try:
        require_github_main_dispatch()
        protocol, execution = load_authority()
        client = PionexPublicClient(
            timeout_seconds=float(execution["execution"]["request_timeout_seconds"]),
            requests_per_second=float(execution["execution"]["requests_per_second"]),
        )
        result = collect_bounded_funding_history(protocol, client)
        report = {
            **base,
            "status": "PASS",
            "provider": protocol["source"]["provider"],
            "symbol": result.symbol,
            "window_start_utc": protocol["source"]["start_utc"],
            "window_end_exclusive_utc": protocol["source"]["end_exclusive_utc"],
            "requests": result.requests,
            "left_boundary_reached": result.left_boundary_reached,
            "first_time_ms": result.first_time_ms,
            "last_time_ms": result.last_time_ms,
            "observation_count": len(result.observations),
            "observations": [
                {
                    "symbol": item.symbol,
                    "funding_time_ms": item.funding_time_ms,
                    "funding_rate": item.funding_rate,
                }
                for item in result.observations
            ],
            "automatic_retries": execution["execution"]["automatic_retries"],
        }
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, PionexFundingHistoryRejected)
            else "runtime failure: " + type(exc).__name__
        )
        report = {**base, "reason": reason}

    output = require_ephemeral_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
