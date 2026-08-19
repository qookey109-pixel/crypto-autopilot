from __future__ import annotations

import importlib.util
import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "infra/render/binance-transport-free/server.py"
CONFIG = ROOT / "config/provider_equivalence_v0_9_render_relay_smoke_v0_1.json"


def _module():
    spec = importlib.util.spec_from_file_location("render_v09", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start(module):
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_v09_smoke_returns_sanitized_pass_but_raw_relay_stays_disabled() -> None:
    module = _module()
    calls = 0

    def fake_fetch():
        nonlocal calls
        calls += 1
        return 200, b'{"symbols":[{"symbol":"BTCUSDT"}]}', "application/json", 872

    module.fetch_exchange_info_raw = fake_fetch
    prior_token = os.environ.get("METADATA_RELAY_TOKEN")
    prior_enabled = os.environ.get("METADATA_RELAY_ENABLED")
    os.environ["METADATA_RELAY_TOKEN"] = "fixture-secret"
    os.environ["METADATA_RELAY_ENABLED"] = "true"
    server, thread = _start(module)
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}{module.METADATA_RELAY_SMOKE_PATH}",
            headers={"Authorization": "Bearer fixture-secret"},
        )
        with urlopen(request, timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["status"] == "PASS"
        assert payload["stage"] == "V0_9_RENDER_RELAY_LIVE_SMOKE_PASS"
        assert payload["upstream_status"] == 200
        assert payload["json_ok"] is True
        assert payload["symbols_array"] is True
        assert payload["symbol_count"] == 872
        assert payload["provider_requests_performed"] == 1
        assert payload["increment_values_emitted"] is False
        assert payload["raw_exchange_info_emitted"] is False
        assert payload["raw_exchange_info_persisted"] is False
        assert payload["r2_client_constructed"] is False
        assert payload["r2_writes_performed"] is False
        assert payload["holdout_candles_accessed"] is False
        assert payload["raw_relay_execution_authorized"] is False
        assert "symbols" not in payload
        assert calls == 1

        raw_request = Request(
            f"http://127.0.0.1:{port}{module.METADATA_RELAY_PATH}",
            headers={"Authorization": "Bearer fixture-secret"},
        )
        try:
            urlopen(raw_request, timeout=5)
            raise AssertionError("raw relay unexpectedly enabled")
        except HTTPError as exc:
            assert exc.code == 503
            disabled = json.loads(exc.read().decode("utf-8"))
        assert disabled["status"] == "DISABLED"
        assert disabled["provider_requests_performed"] == 0
        assert calls == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if prior_token is None:
            os.environ.pop("METADATA_RELAY_TOKEN", None)
        else:
            os.environ["METADATA_RELAY_TOKEN"] = prior_token
        if prior_enabled is None:
            os.environ.pop("METADATA_RELAY_ENABLED", None)
        else:
            os.environ["METADATA_RELAY_ENABLED"] = prior_enabled


def test_v09_wrong_secret_fails_before_provider_request() -> None:
    module = _module()
    calls = 0

    def forbidden_fetch():
        nonlocal calls
        calls += 1
        raise AssertionError("wrong secret reached Binance helper")

    module.fetch_exchange_info_raw = forbidden_fetch
    prior = os.environ.get("METADATA_RELAY_TOKEN")
    os.environ["METADATA_RELAY_TOKEN"] = "expected-secret"
    server, thread = _start(module)
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}{module.METADATA_RELAY_SMOKE_PATH}",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        try:
            urlopen(request, timeout=5)
            raise AssertionError("wrong secret unexpectedly passed")
        except HTTPError as exc:
            assert exc.code == 401
            payload = json.loads(exc.read().decode("utf-8"))
        assert payload["provider_requests_performed"] == 0
        assert payload["r2_writes_performed"] is False
        assert payload["holdout_candles_accessed"] is False
        assert calls == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if prior is None:
            os.environ.pop("METADATA_RELAY_TOKEN", None)
        else:
            os.environ["METADATA_RELAY_TOKEN"] = prior


def test_v09_authority_only_authorizes_sanitized_smoke() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["status"] == "RELAY_LIVE_SMOKE_AUTHORIZED_METADATA_CAPTURE_NOT_AUTHORIZED"
    assert cfg["render"]["plan"] == "free"
    assert cfg["render"]["monthly_budget_usd"] == 0
    assert cfg["render"]["raw_relay_must_remain_disabled"] is True
    assert cfg["execution_boundary"]["relay_smoke_execution_authorized"] is True
    for key in (
        "raw_render_metadata_relay_enablement_authorized",
        "successor_metadata_capture_execution_authorized",
        "successor_schedule_activation_authorized",
        "old_v0_2_schedule_disable_authorized",
        "metadata_r2_writes_authorized",
        "holdout_candle_access_authorized",
        "source_switch_authorized",
        "live_trading_authorized",
    ):
        assert cfg["execution_boundary"][key] is False
