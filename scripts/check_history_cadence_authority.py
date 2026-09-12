"""Read-only preflight for the reviewed two-hour history schedule appendix."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/history_cadence_v0_1.json"
RECEIPT = "research/receipts/2026-09-12-history-cadence-v0-2-authority.json"
CONFIG_SHA = "f7f7141cfd37b0b73b8546a0881a8baee5a80d4da165de39d7695f4b38033df1"
BASE_BINDINGS = {
    "config/binance_usdm_detailed_history_v0_1_2.json": "fc4e42b855229ecb62e12e681778080c2aa749112036a6e8b3af9e9da98b716a",
    "config/binance_usdm_history_recovery_v0_1.json": "6b89660fa7bda95932b93b808f3b54bb3e43421681cc946b801808bc0c7c009b",
    "config/bnx_archive_repair_v0_1.json": "08721e700471fa2a66b686733d21e531ee9216d5607d4a5080d9c2846e985cdd",
}


def validate(root=ROOT, *, env=None, now=None):
    env = os.environ if env is None else env
    now = datetime.now(timezone.utc) if now is None else now
    if (env.get("GITHUB_REPOSITORY") != "qookey109-pixel/crypto-autopilot"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"}
            or env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise ValueError("HISTORY_CADENCE_REQUIRES_FRESH_MAIN_RUN")
    raw = (root / CONFIG).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise ValueError("HISTORY_CADENCE_CONFIG_MISMATCH")
    config = json.loads(raw)
    start = datetime.fromisoformat(config["not_before_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(config["expires_at_utc"].replace("Z", "+00:00"))
    if not start <= now < end:
        raise ValueError("HISTORY_CADENCE_WINDOW_CLOSED")
    receipt = json.loads((root / RECEIPT).read_bytes())
    if (receipt.get("schema") != "history-cadence-authority-v0.2"
            or receipt.get("status") != "AUTHORIZED_ON_PROTECTED_MAIN_MERGE"
            or receipt.get("config") != CONFIG
            or receipt.get("config_sha256") != CONFIG_SHA):
        raise ValueError("HISTORY_CADENCE_RECEIPT_MISMATCH")
    for path, sha in BASE_BINDINGS.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != sha:
            raise ValueError("HISTORY_CADENCE_BASE_AUTHORITY_CHANGED")
    expected = {
        CONFIG,
        ".github/workflows/binance-usdm-detailed-history-v0-1.yml",
        "config/github_automatic_research_operations_v0_2.json",
        "scripts/check_history_cadence_authority.py",
    }
    bindings = receipt.get("bound_files", [])
    if len(bindings) != len(expected) or {r["path"] for r in bindings} != expected:
        raise ValueError("HISTORY_CADENCE_BINDING_SET_MISMATCH")
    for row in bindings:
        if hashlib.sha256((root / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("HISTORY_CADENCE_FILE_MISMATCH")
    return {"status": "PASS", "cron": config["cron"],
            "provider_requests_performed": 0, "r2_access_performed": False}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
