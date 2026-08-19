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


def _module():
    spec = importlib.util.spec_from_file_location("render_secret_preflight_v08", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start(module):
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_shared_secret_preflight_passes_without_provider_or_r2_access() -> None:
    module = _module()
    provider_called = False

    def forbidden_fetch():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("auth-only preflight must never call Binance")

    module.fetch_exchange_info_raw = forbidden_fetch
    prior = os.environ.get("METADATA_RELAY_TOKEN")
    os.environ["METADATA_RELAY_TOKEN"] = "test-shared-secret"
    server, thread = _start(module)
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}{module.METADATA_RELAY_AUTH_CHECK_PATH}",
            headers={"Authorization": "Bearer test-shared-secret"},
        )
        with urlopen(request, timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["status"] == "PASS"
        assert payload["stage"] == "V0_8_SHARED_RELAY_SECRET_MATCH_PRECHECK"
        assert payload["shared_secret_match"] is True
        assert payload["render_metadata_relay_execution_authorized"] is False
        assert payload["render_metadata_relay_enabled"] is False
        assert payload["provider_requests_performed"] == 0
        assert payload["r2_client_constructed"] is False
        assert payload["r2_writes_performed"] is False
        assert payload["holdout_candles_accessed"] is False
        assert provider_called is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if prior is None:
            os.environ.pop("METADATA_RELAY_TOKEN", None)
        else:
            os.environ["METADATA_RELAY_TOKEN"] = prior


def test_shared_secret_preflight_rejects_wrong_token_without_provider_access() -> None:
    module = _module()
    provider_called = False

    def forbidden_fetch():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("mismatched secret must never call Binance")

    module.fetch_exchange_info_raw = forbidden_fetch
    prior = os.environ.get("METADATA_RELAY_TOKEN")
    os.environ["METADATA_RELAY_TOKEN"] = "expected-secret"
    server, thread = _start(module)
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}{module.METADATA_RELAY_AUTH_CHECK_PATH}",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        try:
            urlopen(request, timeout=5)
            raise AssertionError("wrong token unexpectedly passed")
        except HTTPError as exc:
            assert exc.code == 401
            payload = json.loads(exc.read().decode("utf-8"))
        assert payload["status"] == "UNAUTHORIZED"
        assert payload["provider_requests_performed"] == 0
        assert payload["r2_writes_performed"] is False
        assert provider_called is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if prior is None:
            os.environ.pop("METADATA_RELAY_TOKEN", None)
        else:
            os.environ["METADATA_RELAY_TOKEN"] = prior
