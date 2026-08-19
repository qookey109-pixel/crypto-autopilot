from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/provider_equivalence_v0_5_render_free_transport_preflight_v0_1.json"
SERVER = ROOT / "infra/render/binance-transport-free/server.py"


def _module():
    spec = importlib.util.spec_from_file_location("render_transport", SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_render_candidate_is_free_only_and_fail_closed() -> None:
    cfg = json.loads(CONFIG.read_text())
    assert cfg["runtime"]["platform"] == "render"
    assert cfg["runtime"]["instance_type"] == "free"
    assert cfg["runtime"]["region"] == "frankfurt"
    assert cfg["runtime"]["monthly_runtime_budget_usd"] == 0
    assert cfg["runtime"]["payment_method_for_project_forbidden"] is True
    assert cfg["failure_policy"]["upgrade_to_paid_instance"] is False
    assert cfg["failure_policy"]["add_payment_method_to_continue"] is False
    boundary = cfg["authority_boundary"]
    assert boundary["v0_4_koyeb_candidate_status"] == "SUPERSEDED_NOT_EXECUTED"
    for key in (
        "render_transport_authorized_for_metadata_capture",
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


def test_render_server_only_emits_sanitized_transport_metadata() -> None:
    module = _module()
    payload = {"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]}
    result = module.summarize_exchange_info(200, payload)
    assert result["status"] == "PASS"
    assert result["transport"] == "render_free_web_service"
    assert result["symbol_count"] == 2
    forbidden = {"tickSize", "quoteStep", "apiSecret", "secretKey"}
    assert not forbidden.intersection(result)
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["source_switch_performed"] is False
    assert result["live_trading_performed"] is False
