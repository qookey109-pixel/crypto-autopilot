#!/usr/bin/env python3
"""Run one secret-free Pionex historical reach discovery under V0.3 authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from crypto_autopilot.history.pionex_reach_v0_3 import (
    ReachRejected,
    _require_fixed_scope,
    discover_all,
    require_execution_window,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_historical_reach_v0_3.json"
RECEIPT = ROOT / "research/receipts/2026-09-11-pionex-historical-reach-v0-3-authority.json"
CONFIG_SHA256 = "ba7ffaaed06be43fd48348529282d078a7ffcb267957832075097cb5fa6648af"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def load_authority() -> dict[str, object]:
    payload = CONFIG.read_bytes()
    config = json.loads(payload)
    receipt = json.loads(RECEIPT.read_bytes())
    if digest(payload) != CONFIG_SHA256:
        raise ReachRejected("V0.3 config bytes changed")
    if receipt.get("config_sha256") != CONFIG_SHA256:
        raise ReachRejected("V0.3 authority receipt does not bind config")
    if receipt.get("status") != "AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE_MANUAL_DISCOVERY_ONLY":
        raise ReachRejected("V0.3 authority receipt is not executable")
    if config.get("status") != receipt.get("status"):
        raise ReachRejected("V0.3 config/receipt status mismatch")
    if receipt.get("execution_performed_by_this_receipt") is not False:
        raise ReachRejected("authority receipt must not claim execution")
    if receipt.get("yearly_derivation_authorized") is not False:
        raise ReachRejected("V0.3 must not authorize yearly derivation")
    _require_fixed_scope(config)
    require_execution_window(config)
    return config


def main() -> int:
    from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = {
        "schema": "pionex-historical-reach-run-report-v0.3",
        "status": "FAIL",
        "config_sha256": CONFIG_SHA256,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "head_ref": os.environ.get("GITHUB_REF"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "api_key_used": False,
        "raw_provider_payloads_persisted": False,
        "candles_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "materialization_authorized": False,
        "yearly_derivation_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }

    try:
        expected_env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        }
        if any(os.environ.get(key) != value for key, value in expected_env.items()):
            raise ReachRejected("fresh GitHub main manual execution required")
        if not (os.environ.get("GITHUB_RUN_ID") or "").isdigit():
            raise ReachRejected("GitHub run id missing")
        if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
            raise ReachRejected("workflow rerun attempts are not accepted as fresh discovery evidence")

        config = load_authority()
        client = PionexPublicClient(
            timeout_seconds=float(config["request_timeout_seconds"]),
            requests_per_second=float(config["requests_per_second"]),
        )
        result = discover_all(config, client)
        report = {**base, **result, "status": "PASS"}
    except Exception as exc:
        reason = str(exc) if isinstance(exc, ReachRejected) else "runtime failure: " + type(exc).__name__
        report = {**base, "reason": reason}

    output = require_ephemeral_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
