#!/usr/bin/env python3
"""Fail-closed preflight for the retired Core100 History workflow.

This validator preserves the frozen 2026-09-12 cadence evidence without
requiring the current workflow bytes to keep the old cron alive.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
RETIREMENT = Path("config/core100_history_retirement_v0_1.json")
HISTORICAL_CONFIG = Path("config/history_cadence_v0_1.json")
HISTORICAL_RECEIPT = Path(
    "research/receipts/2026-09-12-history-cadence-v0-2-authority.json"
)
CURRENT_WORKFLOW = Path(".github/workflows/binance-usdm-detailed-history-v0-1.yml")
FROZEN_WORKFLOW = Path(
    "research/frozen/workflows/2026-09-12-binance-usdm-detailed-history-v0-1.yml"
)


def _sha256(path: Path, root: Path) -> str:
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def _load(path: Path, root: Path) -> dict[str, object]:
    payload = json.loads((root / path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def validate(
    root: Path = ROOT,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    env = os.environ if env is None else env
    now = datetime.now(timezone.utc) if now is None else now

    if (
        env.get("GITHUB_REPOSITORY") != "qookey109-pixel/crypto-autopilot"
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
    ):
        raise ValueError("CORE100_HISTORY_RETIREMENT_REQUIRES_FRESH_MAIN_MANUAL_RUN")

    retirement = _load(RETIREMENT, root)
    if (
        retirement.get("schema") != "qookey-core100-history-retirement-v0.1"
        or retirement.get("status") != "EFFECTIVE_ON_PROTECTED_MAIN_MERGE"
    ):
        raise ValueError("CORE100_HISTORY_RETIREMENT_CONFIG_MISMATCH")

    completed = retirement.get("completed_evidence")
    retired = retirement.get("retired_execution")
    historical = retirement.get("historical_authority")
    authority = retirement.get("authority")
    if not all(isinstance(item, dict) for item in (completed, retired, historical, authority)):
        raise ValueError("CORE100_HISTORY_RETIREMENT_SHAPE_MISMATCH")
    assert isinstance(completed, dict)
    assert isinstance(retired, dict)
    assert isinstance(historical, dict)
    assert isinstance(authority, dict)

    if (
        completed.get("history_status") != "COMPLETE"
        or completed.get("complete_shards") != 10
        or completed.get("total_shards") != 10
        or completed.get("history_reacquisition_required") is not False
        or retired.get("schedule_trigger_retired") is not True
        or retired.get("generic_auto_discover_backfill_retired") is not True
        or retired.get("automatic_resume") is not False
    ):
        raise ValueError("CORE100_HISTORY_RETIREMENT_COMPLETION_MISMATCH")
    if any(value is not False for value in authority.values()):
        raise ValueError("CORE100_HISTORY_RETIREMENT_GAINED_AUTHORITY")

    workflow = (root / CURRENT_WORKFLOW).read_text(encoding="utf-8")
    if "  schedule:" in workflow or "cron:" in workflow:
        raise ValueError("CORE100_HISTORY_RETIREMENT_CRON_STILL_PRESENT")
    if "  workflow_dispatch:" not in workflow:
        raise ValueError("CORE100_HISTORY_RETIREMENT_MANUAL_ENTRY_MISSING")
    for retired_mode in ("auto", "discover", "backfill"):
        if f"          - {retired_mode}\n" in workflow:
            raise ValueError("CORE100_HISTORY_RETIREMENT_GENERIC_MODE_STILL_PRESENT")

    config = _load(HISTORICAL_CONFIG, root)
    start = datetime.fromisoformat(str(config["not_before_utc"]).replace("Z", "+00:00"))
    end = datetime.fromisoformat(str(config["expires_at_utc"]).replace("Z", "+00:00"))
    if not start <= now < end:
        raise ValueError("CORE100_HISTORY_ORIGINAL_WINDOW_CLOSED")

    receipt = _load(HISTORICAL_RECEIPT, root)
    if (
        receipt.get("schema") != "history-cadence-authority-v0.2"
        or receipt.get("status") != "AUTHORIZED_ON_PROTECTED_MAIN_MERGE"
    ):
        raise ValueError("CORE100_HISTORY_HISTORICAL_RECEIPT_MISMATCH")
    bindings = receipt.get("bound_files")
    if not isinstance(bindings, list):
        raise ValueError("CORE100_HISTORY_HISTORICAL_BINDINGS_MISSING")

    frozen_expected = str(historical.get("frozen_workflow_sha256") or "")
    if _sha256(FROZEN_WORKFLOW, root) != frozen_expected:
        raise ValueError("CORE100_HISTORY_FROZEN_WORKFLOW_MISMATCH")

    mapped_paths = {
        ".github/workflows/binance-usdm-detailed-history-v0-1.yml": FROZEN_WORKFLOW,
    }
    for row in bindings:
        if not isinstance(row, dict):
            raise ValueError("CORE100_HISTORY_HISTORICAL_BINDING_INVALID")
        path = str(row.get("path") or "")
        expected = str(row.get("sha256") or "")
        check_path = mapped_paths.get(path, Path(path))
        if _sha256(check_path, root) != expected:
            raise ValueError(f"CORE100_HISTORY_HISTORICAL_BINDING_CHANGED: {path}")

    return {
        "status": "PASS",
        "stage": "CORE100_HISTORY_RETIRED_MANUAL_REPAIR_ONLY_V0_1",
        "schedule_retired": True,
        "generic_backfill_retired": True,
        "historical_authority_mutated": False,
        "provider_requests_performed": 0,
        "r2_access_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
