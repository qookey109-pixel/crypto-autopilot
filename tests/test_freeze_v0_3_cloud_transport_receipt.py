from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/freeze_v0_3_cloud_transport_receipt.py"
WORKFLOW = ROOT / ".github/workflows/automate-v0-3-cloud-transport-follow-up.yml"


def _module():
    spec = importlib.util.spec_from_file_location("freeze_v0_3_receipt", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "transport": "cloudflare_container",
        "upstream_url": "https://fapi.binance.com/fapi/v1/exchangeInfo",
        "upstream_status": 200,
        "json_ok": True,
        "symbols_array": True,
        "symbol_count": 872,
        "api_key_used": False,
        "increment_values_emitted": False,
        "raw_exchange_info_persisted": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "holdout_candles_accessed": False,
        "holdout_evaluated": False,
        "source_switch_performed": False,
        "live_trading_performed": False,
    }


def test_pass_receipt_never_grants_downstream_authority() -> None:
    module = _module()
    receipt = module.build_receipt(
        payload=_payload(),
        run_id=123,
        run_url="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/123",
        head_sha="a" * 40,
        observed_at="2026-08-19T10:00:00Z",
    )
    assert receipt["stage"] == "V0_3_CLOUDFLARE_CONTAINER_BINANCE_TRANSPORT_PASS"
    boundary = receipt["authority_boundary"]
    assert boundary["transport_preflight_passed"] is True
    assert boundary["cloud_transport_authorized_for_metadata_capture"] is False
    assert boundary["metadata_capture_execution_authorized_by_this_receipt"] is False
    assert boundary["holdout_candle_access_authorized"] is False
    assert boundary["source_switch_authorized"] is False
    assert boundary["backtest_admission_authorized"] is False
    assert boundary["automatic_trade_plan_authorized"] is False
    assert boundary["real_money_order_authorized"] is False
    assert boundary["live_trading_authorized"] is False


def test_blocked_or_unsanitized_results_fail_closed() -> None:
    module = _module()
    blocked = _payload()
    blocked["status"] = "BLOCKED"
    try:
        module.validate_sanitized_pass(blocked)
    except ValueError:
        pass
    else:
        raise AssertionError("BLOCKED evidence must not freeze as PASS")

    leaked = _payload()
    leaked["tickSize"] = "0.10"
    try:
        module.validate_sanitized_pass(leaked)
    except ValueError:
        pass
    else:
        raise AssertionError("unsanitized increment metadata must be rejected")


def test_follow_up_workflow_is_retired_without_automatic_or_write_authority() -> None:
    text = WORKFLOW.read_text()
    assert "name: Retired V0.3 Cloudflare Container Follow-up" in text
    assert "workflow_dispatch:" in text
    assert "workflow_run:" not in text
    assert "push:" not in text
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "pull-requests: write" not in text
    assert "issues: write" not in text
    assert "status=RETIRED_NO_EXECUTION" in text
    assert "provider_requests_performed=0" in text
    assert "r2_writes_performed=false" in text
    assert "holdout_candles_accessed=false" in text
    assert "source_switch_authorized=false" in text
    assert "live_trading_authorized=false" in text
