from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/post_window_paper_training_v0_2.json"
RECEIPT = (
    ROOT
    / "research/receipts/2026-08-29-post-window-paper-training-v0-2-prepared.json"
)
WORKFLOWS = ROOT / ".github/workflows"


def test_successor_is_hash_bound_and_cannot_activate_itself() -> None:
    config_bytes = CONFIG.read_bytes()
    config = json.loads(config_bytes)
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["config_sha256"] == hashlib.sha256(config_bytes).hexdigest()
    assert config["status"] == "PREPARED_WAITING_FOR_HOLDOUT_AUTHORITY"
    assert config["proposed_execution"]["automatic_activation"] is False
    assert config["proposed_execution"]["workflow_created"] is False
    assert all(value is False for value in config["authority"].values())
    assert config["activation_gates"]["activation_authorized"] is False
    assert config["activation_gates"]["separate_holdout_access_authority_merged"] is False


def test_successor_has_no_active_workflow_or_hidden_schedule() -> None:
    execution_references = []
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        if CONFIG.name in text and path.name != "dashboard-github-pages.yml":
            execution_references.append(path.name)
    assert execution_references == []
    dashboard = (WORKFLOWS / "dashboard-github-pages.yml").read_text(encoding="utf-8")
    assert CONFIG.name in dashboard


def test_successor_preserves_existing_broker_and_live_trading_boundary() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    resume = config["resume_contract"]
    assert resume["reuse_existing_paper_broker"] is True
    assert resume["reuse_existing_pionex_public_adapter"] is True
    assert resume["forced_trade_count"] is False
    assert resume["pionex_demo_manual_sampling_only"] is True
    assert config["authority"]["real_money_order_authorized"] is False
    assert config["authority"]["live_trading_authorized"] is False
