from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/provider_equivalence_v0_4_koyeb_free_transport_preflight_v0_1.json"
SERVER = ROOT / "infra/koyeb/binance-transport-free/server.py"


def _module():
    spec = importlib.util.spec_from_file_location("koyeb_free_transport_server", SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_koyeb_preflight_is_zero_cost_and_diagnostic_only() -> None:
    cfg = json.loads(CONFIG.read_text())
    assert cfg["status"] == "PREFLIGHT_PREPARED_NOT_EXECUTED"
    runtime = cfg["runtime"]
    assert runtime["platform"] == "koyeb"
    assert runtime["service_type"] == "WEB"
    assert runtime["instance_type"] == "free"
    assert runtime["region"] == "fra"
    assert runtime["monthly_runtime_budget_usd"] == 0
    assert cfg["diagnostic"]["official_endpoint"] == "https://fapi.binance.com/fapi/v1/exchangeInfo"
    assert cfg["diagnostic"]["api_key_required"] is False
    assert cfg["diagnostic"]["private_api_credentials_forbidden"] is True
    assert cfg["failure_policy"]["upgrade_to_paid_instance"] is False


def test_bearer_auth_is_required() -> None:
    module = _module()
    assert module.is_authorized(None, "abc") is False
    assert module.is_authorized("Bearer abc", None) is False
    assert module.is_authorized("abc", "abc") is False
    assert module.is_authorized("Bearer wrong", "abc") is False
    assert module.is_authorized("Bearer abc", "abc") is True


def test_sanitizer_never_emits_increment_values() -> None:
    module = _module()
    payload = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
                ],
            }
        ]
    }
    result = module.summarize_exchange_info(200, payload)
    assert result["status"] == "PASS"
    assert result["transport"] == "koyeb_free_web_service"
    assert result["symbol_count"] == 1
    assert result["api_key_used"] is False
    assert result["increment_values_emitted"] is False
    assert result["raw_exchange_info_persisted"] is False
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["source_switch_performed"] is False
    assert result["live_trading_performed"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "tickSize" not in serialized
    assert "0.10" not in serialized


def test_non_200_transport_fails_closed() -> None:
    module = _module()
    result = module.summarize_exchange_info(451, {"symbols": [{"symbol": "BTCUSDT"}]})
    assert result["status"] == "BLOCKED"
    assert result["upstream_status"] == 451


def test_v0_4_does_not_open_any_downstream_authority() -> None:
    cfg = json.loads(CONFIG.read_text())
    boundary = cfg["authority_boundary"]
    assert boundary["v0_1_equivalence_status"] == "FAIL"
    assert boundary["v0_1_mutated"] is False
    assert boundary["v0_2_active_transport"] == "github_self_hosted_mac"
    assert boundary["v0_2_self_hosted_mac_transport_authority_mutated"] is False
    for key in (
        "koyeb_transport_authorized_for_metadata_capture",
        "metadata_capture_execution_authorized",
        "holdout_candle_access_authorized",
        "source_switch_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False, key
