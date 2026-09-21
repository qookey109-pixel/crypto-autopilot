from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import check_core100_history_retirement_v0_1 as gate


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/binance-usdm-detailed-history-v0-1.yml"
FROZEN = ROOT / "research/frozen/workflows/2026-09-12-binance-usdm-detailed-history-v0-1.yml"
RECEIPT = ROOT / "research/receipts/2026-09-12-history-cadence-v0-2-authority.json"
RETIREMENT = ROOT / "config/core100_history_retirement_v0_1.json"
ENV = {
    "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_RUN_ATTEMPT": "1",
}
NOW = datetime(2026, 9, 21, 3, 0, tzinfo=timezone.utc)


def test_retired_history_workflow_has_no_cron_or_generic_backfill() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "  schedule:" not in text
    assert "cron:" not in text
    assert "  workflow_dispatch:" in text
    assert "  backfill:" not in text
    for retired_mode in ("auto", "discover", "backfill"):
        assert f"          - {retired_mode}\n" not in text
    for retained_mode in ("diagnose-bnx", "repair-bnx-1h", "repair-bnx-bundle"):
        assert f"          - {retained_mode}\n" in text
    assert "check_core100_history_retirement_v0_1.py" in text
    assert "check_history_cadence_authority.py" not in text


def test_retirement_preflight_preserves_frozen_history_boundary() -> None:
    result = gate.validate(env=ENV, now=NOW)
    assert result["status"] == "PASS"
    assert result["schedule_retired"] is True
    assert result["generic_backfill_retired"] is True
    assert result["historical_authority_mutated"] is False
    assert result["provider_requests_performed"] == 0
    assert result["r2_access_performed"] is False


def test_retirement_preflight_rejects_schedule_branch_and_rerun() -> None:
    for key, value in (
        ("GITHUB_EVENT_NAME", "schedule"),
        ("GITHUB_REF", "refs/heads/feature/test"),
        ("GITHUB_RUN_ATTEMPT", "2"),
    ):
        with pytest.raises(ValueError, match="FRESH_MAIN_MANUAL_RUN"):
            gate.validate(env=dict(ENV, **{key: value}), now=NOW)


def test_frozen_workflow_matches_historical_receipt_exactly() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    row = next(
        item
        for item in receipt["bound_files"]
        if item["path"] == ".github/workflows/binance-usdm-detailed-history-v0-1.yml"
    )
    assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == row["sha256"]
    retirement = json.loads(RETIREMENT.read_text(encoding="utf-8"))
    assert retirement["historical_authority"]["frozen_workflow_sha256"] == row["sha256"]


def test_retirement_grants_no_new_authority() -> None:
    retirement = json.loads(RETIREMENT.read_text(encoding="utf-8"))
    assert retirement["completed_evidence"]["history_status"] == "COMPLETE"
    assert retirement["completed_evidence"]["complete_shards"] == 10
    assert retirement["completed_evidence"]["history_reacquisition_required"] is False
    assert retirement["retired_execution"]["automatic_resume"] is False
    assert all(value is False for value in retirement["authority"].values())
