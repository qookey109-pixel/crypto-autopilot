from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/provider_equivalence_v0_3_cloud_transport_preflight_v0_1.json"
SERVER = ROOT / "infra/cloudflare/binance-transport-container/server.py"


def _server_module():
    spec = importlib.util.spec_from_file_location("cloud_transport_server", SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cloud_transport_preflight_is_diagnostic_only() -> None:
    cfg = json.loads(CONFIG.read_text())
    assert cfg["status"] == "PREFLIGHT_PREPARED_NOT_EXECUTED"
    assert cfg["authority_boundary"]["v0_1_equivalence_status"] == "FAIL"
    assert cfg["authority_boundary"]["v0_1_mutated"] is False
    assert cfg["authority_boundary"]["v0_2_active_transport"] == "github_self_hosted_mac"
    assert cfg["authority_boundary"]["cloud_transport_authorized_for_metadata_capture"] is False
    assert cfg["diagnostic"]["official_endpoint"] == "https://fapi.binance.com/fapi/v1/exchangeInfo"
    assert cfg["diagnostic"]["api_key_required"] is False
    assert cfg["diagnostic"]["private_api_credentials_forbidden"] is True
    assert cfg["diagnostic"]["r2_writes_performed"] is False
    assert cfg["diagnostic"]["holdout_candles_accessed"] is False
    assert cfg["diagnostic"]["source_switch_performed"] is False
    assert cfg["diagnostic"]["live_trading_performed"] is False
    auth = cfg["authorization_boundary"]
    assert auth["metadata_capture_execution_authorized"] is False
    assert auth["holdout_candle_access_authorized"] is False
    assert auth["source_switch_authorized"] is False
    assert auth["backtest_admission_authorized"] is False
    assert auth["automatic_trade_plan_authorized"] is False
    assert auth["real_money_order_authorized"] is False
    assert auth["live_trading_authorized"] is False


def test_sanitizer_never_emits_price_increment_values() -> None:
    module = _server_module()
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
    assert result["symbol_count"] == 1
    assert result["increment_values_emitted"] is False
    assert result["api_key_used"] is False
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["source_switch_performed"] is False
    assert result["live_trading_performed"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "tickSize" not in serialized
    assert "0.10" not in serialized


def test_non_200_transport_fails_closed() -> None:
    module = _server_module()
    result = module.summarize_exchange_info(403, {"symbols": [{"symbol": "BTCUSDT"}]})
    assert result["status"] == "BLOCKED"
    assert result["upstream_status"] == 403
