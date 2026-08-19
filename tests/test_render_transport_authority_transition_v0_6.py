from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/provider_equivalence_v0_6_render_transport_authority_transition_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-08-19-provider-equivalence-v0-6-render-transport-authority-transition.json"


def test_v0_6_transition_preserves_v0_2_and_stays_non_executing() -> None:
    cfg = json.loads(CONFIG.read_text())
    receipt = json.loads(RECEIPT.read_text())

    assert cfg["status"] == "TRANSPORT_AUTHORITY_TRANSITION_FROZEN"
    transition = cfg["transition"]
    assert transition["prior_transport_authority"] == "github_self_hosted_mac"
    assert transition["new_transport_authority_for_successor_public_metadata_protocol"] == "render_free_web_service"
    assert transition["runtime_region"] == "frankfurt"
    assert transition["runtime_plan"] == "free"
    assert transition["monthly_runtime_budget_usd"] == 0
    assert transition["v0_2_historical_authority_preserved"] is True
    assert transition["v0_2_receipt_mutated"] is False
    assert transition["v0_2_metadata_capture_protocol_mutated"] is False
    assert transition["successor_metadata_capture_protocol_required_before_execution"] is True

    api = cfg["binance_api_key_boundary"]
    assert api["public_exchange_info_requires_api_key"] is False
    assert api["api_key_used_in_v0_5_preflight"] is False
    assert api["project_wide_binance_api_key_prohibition_declared"] is False
    assert api["api_key_bypass_for_transport_failure_authorized"] is False
    assert api["future_authenticated_binance_api_may_be_versioned_separately"] is True

    assert receipt["status"] == "PASS"
    assert receipt["prerequisite_evidence"]["v0_5_upstream_status"] == 200
    assert receipt["prerequisite_evidence"]["v0_5_json_ok"] is True
    assert receipt["prerequisite_evidence"]["v0_5_symbols_array"] is True
    assert receipt["prerequisite_evidence"]["v0_5_symbol_count"] > 0
    assert receipt["decision"]["v0_2_authority_overwritten"] is False
    assert receipt["decision"]["render_metadata_capture_execution_authorized_by_this_receipt"] is False
    assert receipt["api_key_interpretation"]["this_receipt_declares_project_wide_binance_api_key_ban"] is False

    for value in cfg["execution_boundary"].values():
        assert value is False
    for value in receipt["authorization_boundary"].values():
        assert value is False


def test_v0_6_transition_remains_fail_closed_and_free_only() -> None:
    cfg = json.loads(CONFIG.read_text())
    failure = cfg["failure_policy"]
    assert failure["render_unavailable"] == "FAIL_CLOSED"
    assert failure["render_free_allowance_exhausted"] == "FAIL_CLOSED"
    assert failure["binance_403_or_451"] == "FAIL_CLOSED"
    assert failure["invalid_json"] == "FAIL_CLOSED"
    assert failure["empty_symbols"] == "FAIL_CLOSED"
    assert failure["use_proxy_bypass"] is False
    assert failure["switch_endpoint"] is False
    assert failure["use_binance_api_key_as_transport_bypass"] is False
    assert failure["upgrade_to_paid_render_instance"] is False
    assert failure["add_payment_method_to_continue"] is False
