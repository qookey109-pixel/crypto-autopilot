from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/receipts/2026-08-19-provider-equivalence-v0-5-render-free-transport-pass.json"


def test_render_v0_5_pass_receipt_is_sanitized_and_non_authorizing() -> None:
    receipt = json.loads(RECEIPT.read_text())
    evidence = receipt["execution_evidence"]
    safety = receipt["sanitization_and_safety"]
    boundary = receipt["authorization_boundary"]

    assert receipt["status"] == "PASS"
    assert evidence["transport"] == "render_free_web_service"
    assert evidence["runtime_region"] == "frankfurt"
    assert evidence["upstream_url"] == "https://fapi.binance.com/fapi/v1/exchangeInfo"
    assert evidence["upstream_status"] == 200
    assert evidence["json_ok"] is True
    assert evidence["symbols_array"] is True
    assert evidence["symbol_count"] > 0

    for key in (
        "api_key_used",
        "increment_values_emitted",
        "raw_exchange_info_persisted",
        "r2_client_constructed",
        "r2_writes_performed",
        "holdout_candles_accessed",
        "holdout_evaluated",
        "source_switch_performed",
        "live_trading_performed",
        "diagnostic_token_value_recorded",
    ):
        assert safety[key] is False

    assert receipt["authority_interpretation"]["v0_2_self_hosted_mac_transport_authority_preserved"] is True
    assert receipt["authority_interpretation"]["this_pass_replaces_v0_2_authority"] is False

    for key, value in boundary.items():
        assert value is False, key
