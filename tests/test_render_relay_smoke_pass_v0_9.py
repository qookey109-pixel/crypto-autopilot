from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/receipts/2026-08-20-provider-equivalence-v0-9-render-relay-smoke-pass.json"


def test_v09_relay_smoke_pass_receipt_is_sanitized_and_non_authorizing() -> None:
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert r["status"] == "PASS"
    assert r["stage"] == "PROVIDER_EQUIVALENCE_V0_9_RENDER_RELAY_LIVE_SMOKE_PASS"
    assert r["execution"]["workflow_run_id"] == 32275517138
    assert r["execution"]["head_sha"] == "a35be3407f6b29ca88b9a723740cb147dcd35fe0"
    assert r["execution"]["issue_comment_id"] == 5344959081
    assert r["execution"]["render_deploy_id"] == "dep-da2tgdqd0e5s7386qghg"

    result = r["result"]
    assert result["upstream_status"] == 200
    assert result["json_ok"] is True
    assert result["symbols_array"] is True
    assert result["symbol_count"] == 872
    assert result["provider_requests_performed"] == 1
    for key in (
        "api_key_used",
        "increment_values_emitted",
        "raw_exchange_info_emitted",
        "raw_exchange_info_persisted",
        "r2_client_constructed",
        "r2_writes_performed",
        "holdout_candles_accessed",
        "source_switch_performed",
        "live_trading_performed",
        "raw_relay_execution_authorized",
        "successor_capture_execution_authorized",
    ):
        assert result[key] is False

    interpretation = r["interpretation"]
    assert interpretation["render_authenticated_binance_transport_proven_for_successor_smoke"] is True
    assert interpretation["old_v0_2_schedule_remains_current"] is True
    for key in (
        "raw_metadata_relay_authorized_by_this_receipt",
        "successor_metadata_capture_authorized_by_this_receipt",
        "successor_schedule_authorized_by_this_receipt",
        "metadata_r2_writes_authorized_by_this_receipt",
        "holdout_access_authorized_by_this_receipt",
        "final_atomic_cutover_authorized_by_this_receipt",
    ):
        assert interpretation[key] is False


def test_v09_receipt_contains_no_secret_or_raw_exchange_info() -> None:
    text = RECEIPT.read_text(encoding="utf-8")
    assert "Bearer " not in text
    assert "METADATA_RELAY_TOKEN=" not in text
    assert '"symbols": [' not in text
    assert "tickSize" not in text
