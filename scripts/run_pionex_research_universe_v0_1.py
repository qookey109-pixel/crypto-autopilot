#!/usr/bin/env python3
"""Run one bounded public Pionex 150+ universe snapshot after authority merge."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path

from crypto_autopilot.research.pionex_universe_execution_v0_1 import (
    UniverseExecutionRejected,
    capture_public_snapshot,
    validate_execution_config,
)


ROOT = Path(__file__).resolve().parents[1]
EXEC_CONFIG = ROOT / "config/pionex_research_universe_execution_v0_1.json"
SELECTION_CONFIG = ROOT / "config/pionex_research_universe_v0_1.json"
ALT_REGISTRY = ROOT / "config/pionex_alternative_assets_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-11-pionex-research-universe-execution-v0-1-authority.json"
EXEC_CONFIG_SHA256 = "a7c898d24e4cc5a6685746559fc1aeb49a6841b471f1dd6a78d1d8ff84262d4a"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def load_authority() -> tuple[dict[str, object], bytes, bytes]:
    exec_bytes = EXEC_CONFIG.read_bytes()
    selection_bytes = SELECTION_CONFIG.read_bytes()
    alt_bytes = ALT_REGISTRY.read_bytes()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if digest(exec_bytes) != EXEC_CONFIG_SHA256:
        raise UniverseExecutionRejected("execution config bytes changed")
    if receipt.get("config_sha256") != EXEC_CONFIG_SHA256:
        raise UniverseExecutionRejected("authority receipt does not bind execution config")
    if receipt.get("status") != "AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE_AWAITING_WORKFLOW_WIRING":
        raise UniverseExecutionRejected("authority receipt is not executable")
    config = json.loads(exec_bytes)
    if config.get("status") != receipt.get("status"):
        raise UniverseExecutionRejected("execution config/receipt status mismatch")
    if receipt.get("execution_performed_by_this_receipt") is not False:
        raise UniverseExecutionRejected("authority receipt cannot claim execution")
    validate_execution_config(
        config,
        selection_config_bytes=selection_bytes,
        alternative_registry_bytes=alt_bytes,
    )
    return config, selection_bytes, alt_bytes


def require_github_main_dispatch() -> None:
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise UniverseExecutionRejected("fresh GitHub main workflow_dispatch attempt 1 required")
    if not (os.environ.get("GITHUB_RUN_ID") or "").isdigit():
        raise UniverseExecutionRejected("GitHub run id missing")


def main() -> int:
    from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = {
        "schema": "pionex-research-universe-run-report-v0.1",
        "status": "FAIL",
        "execution_config_sha256": EXEC_CONFIG_SHA256,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "head_ref": os.environ.get("GITHUB_REF"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "api_key_used": False,
        "private_account_data_accessed": False,
        "raw_provider_payloads_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }

    try:
        require_github_main_dispatch()
        config, selection_bytes, alt_bytes = load_authority()
        client = PionexPublicClient(
            timeout_seconds=float(config["execution"]["request_timeout_seconds"]),
            requests_per_second=float(config["execution"]["requests_per_second"]),
        )
        report = {
            **base,
            **capture_public_snapshot(
                config,
                selection_config_bytes=selection_bytes,
                alternative_registry_bytes=alt_bytes,
                client=client,
                observed_at=datetime.now(UTC),
            ),
            "status": "PASS",
        }
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, UniverseExecutionRejected)
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
