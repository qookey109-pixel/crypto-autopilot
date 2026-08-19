from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/receipts/2026-08-19-provider-equivalence-v0-8-shared-relay-secret-handshake-pass.json"


def test_v08_shared_secret_handshake_receipt_is_sanitized_pass_only() -> None:
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert r["status"] == "PASS"
    assert r["stage"] == "PROVIDER_EQUIVALENCE_V0_8_SHARED_RELAY_SECRET_HANDSHAKE_PASS"
    assert r["execution"]["workflow_run_id"] == 32273314648
    assert r["execution"]["head_sha"] == "5991931fac032e7a509a72ac9d9a4d551c531d87"
    assert r["execution"]["issue_comment_id"] == 5344681183
    result = r["result"]
    assert result["shared_secret_match"] is True
    assert result["secret_value_recorded"] is False
    assert result["provider_requests_performed"] == 0
    assert result["r2_client_constructed"] is False
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["render_relay_execution_authorized"] is False
    assert result["successor_capture_execution_authorized"] is False
    interpretation = r["interpretation"]
    assert interpretation["proves_matching_out_of_band_secret_presence"] is True
    assert interpretation["authorizes_final_cutover"] is False
    assert interpretation["v0_2_self_hosted_capture_path_remains_current"] is True
    boundary = r["scientific_boundary"]
    assert boundary["replacement_holdout_state"] == "FROZEN_UNOPENED"
    for key in (
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False


def test_receipt_does_not_contain_secret_material() -> None:
    text = RECEIPT.read_text(encoding="utf-8")
    assert "Bearer " not in text
    assert "DIAGNOSTIC_TOKEN=" not in text
    assert "METADATA_RELAY_TOKEN=" not in text
