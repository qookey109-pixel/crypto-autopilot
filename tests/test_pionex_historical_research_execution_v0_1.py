from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_historical_research_execution_v0_1.json"
PREPARED = ROOT / "config/pionex_historical_research_pool_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-10-pionex-historical-research-execution-v0-1-authority.json"
WORKFLOW = ROOT / ".github/workflows/pionex-historical-research-execution-v0-1.yml"
SCRIPT = ROOT / "scripts/run_pionex_historical_research_execution_v0_1.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_execution_authority_is_sha_bound_and_one_shot_only() -> None:
    config = json.loads(CONFIG.read_text())
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["config_sha256"] == sha256(CONFIG)
    assert receipt["prepared_pool_config_sha256"] == sha256(PREPARED)
    assert config["execution"]["trigger"] == "workflow_dispatch_only"
    assert config["pilot"]["symbol"] == "BTC_USDT_PERP"
    assert config["pilot"]["intervals"] == ["15M", "60M", "4H"]
    assert config["pilot"]["full_150_market_materialization_authorized"] is False
    assert config["storage"]["free_only_hard_stop_bytes"] == 8_000_000_000


def test_execution_boundary_remains_paper_only() -> None:
    authority = json.loads(CONFIG.read_text())["authority"]
    assert authority["public_pionex_kline_reads_authorized"] is True
    assert authority["production_r2_pilot_writes_authorized"] is True
    for key in (
        "automatic_schedule_authorized",
        "replacement_holdout_access_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "training_authorized",
        "source_switch_authorized",
        "binance_relabel_as_pionex_authorized",
        "private_api_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert authority[key] is False


def test_workflow_is_serialized_and_has_no_trading_or_schedule_path() -> None:
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "  schedule:" not in text
    assert "cancel-in-progress: false" in text
    assert "persist-credentials: false" in text
    assert "R2_SECRET_ACCESS_KEY" in text
    assert "PIONEX_API_KEY" not in text
    assert "place_order" not in text.lower()


def test_workflow_is_classified_without_adding_a_cron() -> None:
    convergence = json.loads(
        (ROOT / "config/project_convergence_v0_1.json").read_text(encoding="utf-8")
    )
    classified = {
        name
        for group in convergence["workflow_groups"].values()
        for name in group
    }
    assert "pionex-historical-research-execution-v0-1.yml" in classified
    scheduled = [
        item
        for group in convergence["scheduled_workflows"].values()
        for item in group
        if item.get("cron_utc")
    ]
    assert len(scheduled) == 7


def test_runner_requires_headroom_before_pionex_history_and_writes_pointer_last() -> None:
    text = SCRIPT.read_text()
    assert text.index("before_provider = current_bucket_bytes(store)") < text.index("client = PionexPublicClient")
    assert "PIONEX_HISTORICAL_RESEARCH_PILOT_ALREADY_COMPLETE" in text
    assert text.index("receipt_key, manifest_key") < text.index("latest = {")
    assert "get_bytes_verified(storage[\"latest_pointer_key\"]" in text
