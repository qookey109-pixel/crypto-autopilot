from __future__ import annotations

import hashlib
import json
from pathlib import Path

from crypto_autopilot.research.automation_health import (
    expectation_from_config,
    validate_schedule_coverage,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/github_automatic_research_operations_v0_1.json"
HEALTH = ROOT / "config/research_automation_health_v0_2.json"
RECEIPT = (
    ROOT
    / "research/receipts/2026-09-01-github-automatic-research-operations-v0-1-authority.json"
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_policy_matches_every_repository_cron_exactly() -> None:
    policy = _load(POLICY)
    scheduled = {
        row["workflow"]: row["cron_utc"] for row in policy["scheduled_workflows"]
    }
    health = _load(HEALTH)
    expectations = [expectation_from_config(row) for row in health["workflows"]]
    coverage = validate_schedule_coverage(expectations, ROOT / ".github/workflows")
    assert coverage["complete"] is True
    assert coverage["scheduled_workflow_count"] == 7
    assert coverage["workflows"] == scheduled


def test_manual_runs_are_not_normal_operations_or_health_evidence() -> None:
    policy = _load(POLICY)
    normal = policy["normal_operation"]
    assert normal["manual_dispatch_required"] is False
    assert normal["manual_dispatch_counts_as_automation_health"] is False
    health = _load(HEALTH)
    assert all(row["allowed_events"] == ["schedule"] for row in health["workflows"])


def test_automation_adds_no_holdout_model_or_trading_authority() -> None:
    policy = _load(POLICY)
    assert policy["authority"]["github_actions_metadata_read_only"] is True
    for key, value in policy["authority"].items():
        if key != "github_actions_metadata_read_only":
            assert value is False, key
    health = _load(HEALTH)
    assert health["authority"]["github_actions_metadata_read_only"] is True
    for key, value in health["authority"].items():
        if key != "github_actions_metadata_read_only":
            assert value is False, key


def test_authority_receipt_binds_current_control_plane() -> None:
    receipt = _load(RECEIPT)
    assert receipt["status"] == "AUTHORIZED_ON_PROTECTED_MAIN_MERGE"
    for row in receipt["bound_files"]:
        payload = (ROOT / row["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == row["sha256"]
    assert all(value is False for value in receipt["explicitly_not_authorized"].values())
