from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/cloud_transport_automation_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/dispatch-v0-3-cloud-transport-from-authority-marker.yml"


def test_dispatch_marker_is_one_shot_and_diagnostic_only() -> None:
    cfg = json.loads(CONFIG.read_text())
    assert cfg["status"] == "V0_3_DIAGNOSTIC_DISPATCH_AUTHORIZED"
    assert cfg["dispatch_generation"] == 1
    assert cfg["target_ref"] == "main"
    policy = cfg["automation_policy"]
    assert policy["dispatch_on_marker_merge_to_main"] is True
    assert policy["manual_run_button_required"] is False
    assert policy["scheduled_repeat"] is False
    assert policy["retry_loop"] is False

    boundary = cfg["authority_boundary"]
    assert boundary["v0_1_equivalence_status"] == "FAIL"
    assert boundary["v0_1_mutated"] is False
    assert boundary["v0_2_self_hosted_mac_transport_authority_mutated"] is False
    for key in (
        "cloud_transport_authorized_for_metadata_capture",
        "metadata_capture_execution_authorized",
        "holdout_candle_access_authorized",
        "source_switch_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False


def test_dispatch_workflow_is_retired_without_automatic_or_external_execution() -> None:
    text = WORKFLOW.read_text()
    assert "name: Retired V0.3 Cloudflare Container Dispatch" in text
    assert "workflow_dispatch:" in text
    assert "push:" not in text
    assert "workflow_run:" not in text
    assert "contents: read" in text
    assert "actions: write" not in text
    assert "contents: write" not in text
    assert "issues: write" not in text
    assert "pull-requests: write" not in text
    assert "status=RETIRED_NO_EXECUTION" in text
    assert "workflow_dispatch_to_container_performed=false" in text
    assert "provider_requests_performed=0" in text
    assert "r2_writes_performed=false" in text
    assert "holdout_candles_accessed=false" in text
    assert "source_switch_authorized=false" in text
    assert "live_trading_authorized=false" in text
