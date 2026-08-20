from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from crypto_autopilot import provider_metadata_capture_v0_2 as v02
from crypto_autopilot import provider_metadata_capture_v0_10 as v10
from crypto_autopilot.storage.r2 import R2ObjectReceipt

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "infra/render/binance-transport-free/server.py"
CONFIG = ROOT / "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json"
AUTHORITY = ROOT / "research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json"
OLD_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-2-metadata-capture.yml"
NEW_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"


def _server_module():
    spec = importlib.util.spec_from_file_location("render_v010", SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start(module):
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _vector(prefix: str) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "symbol": f"{prefix}{i:02d}",
            "price_increment": "0.01",
            "status": "TRADING",
            "contract_type": "PERPETUAL",
            "source_field": "fixture",
        }
        for i in range(15)
    )


def _payloads():
    protocol, _, _ = v02.load_and_validate_authority()
    pionex = v02.ProviderPayload(
        provider="pionex",
        raw=b'{"fixture":"pionex-v010"}',
        content_type="application/json",
        vector=_vector("P"),
    )
    binance = v02.ProviderPayload(
        provider="binance_usdm",
        raw=b'{"fixture":"binance-v010"}',
        content_type="application/json",
        vector=_vector("B"),
    )
    return pionex, binance, protocol


class FakePaginator:
    def __init__(self, sizes: list[int]):
        self.sizes = sizes

    def paginate(self, *, Bucket: str):  # noqa: N803
        assert Bucket == "test-bucket"
        yield {"Contents": [{"Size": size} for size in self.sizes]}


class FakeClient:
    def __init__(self, sizes: list[int]):
        self.sizes = sizes

    def get_paginator(self, name: str):
        assert name == "list_objects_v2"
        return FakePaginator(self.sizes)


class FakeStore:
    def __init__(self, *, initial_sizes: list[int] | None = None):
        self.bucket = "test-bucket"
        self.client = FakeClient(initial_sizes or [])
        self.objects: dict[str, bytes] = {}
        self.put_order: list[str] = []

    def exists(self, key: str) -> bool:
        return key in self.objects

    def put_bytes(self, key: str, payload: bytes, **kwargs):
        assert key not in self.objects
        self.objects[key] = payload
        self.put_order.append(key)
        sha = hashlib.sha256(payload).hexdigest()
        return R2ObjectReceipt(
            bucket=self.bucket,
            key=key,
            bytes=len(payload),
            sha256=sha,
            etag="fixture",
        )

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        payload = self.objects[key]
        assert hashlib.sha256(payload).hexdigest() == expected_sha256
        return payload


def test_final_authority_is_effective_only_on_merge_and_preserves_boundaries() -> None:
    cfg, authority, smoke = v10.validate_final_atomic_cutover_authority()
    assert cfg["effectivity"]["effective_before_merge"] is False
    assert cfg["effectivity"]["effective_only_when_exact_change_set_is_merged_to_main"] is True
    assert authority["effectivity"]["requires_human_review_before_merge"] is True
    assert smoke["result"]["upstream_status"] == 200
    assert smoke["result"]["symbol_count"] == 872
    assert cfg["scientific_scope"]["replacement_holdout_state"] == "FROZEN_UNOPENED"
    assert cfg["render_transport"]["plan"] == "free"
    assert cfg["render_transport"]["monthly_budget_usd"] == 0
    assert cfg["render_transport"]["render_receives_r2_credentials"] is False
    assert cfg["storage"]["free_only_operational_hard_stop_bytes"] == 8_000_000_000
    assert cfg["atomic_repository_cutover"]["concurrent_old_and_new_capture_paths_authorized"] is False
    assert cfg["api_key_interpretation"]["project_wide_binance_api_key_ban_declared"] is False
    assert cfg["api_key_interpretation"]["binance_api_key_transport_bypass_authorized"] is False


def test_atomic_workflow_cutover_has_no_old_schedule_and_window_scoped_new_schedule() -> None:
    old = OLD_WORKFLOW.read_text(encoding="utf-8").splitlines()
    new = NEW_WORKFLOW.read_text(encoding="utf-8").splitlines()
    assert not any(line == "  schedule:" for line in old)
    assert not any("runs-on: [self-hosted" in line for line in old)
    assert any(line == "  schedule:" for line in new)
    for cron in (
        '    - cron: "17,47 * 27-31 8 *"',
        '    - cron: "17,47 * 1-3 9 *"',
        '    - cron: "17,47 0-1 4 9 *"',
    ):
        assert cron in new
    assert "runs-on: ubuntu-latest" in NEW_WORKFLOW.read_text(encoding="utf-8")


def test_v010_raw_relay_returns_exact_fixture_while_v07_raw_relay_stays_disabled() -> None:
    module = _server_module()
    calls = 0
    raw_fixture = b'{"symbols":[{"symbol":"BTCUSDT"}],"fixture":"v010"}'

    def fake_fetch():
        nonlocal calls
        calls += 1
        return 200, raw_fixture, "application/json", 872

    module.fetch_exchange_info_raw = fake_fetch
    prior_token = os.environ.get("METADATA_RELAY_TOKEN")
    prior_enabled = os.environ.get("METADATA_RELAY_ENABLED")
    os.environ["METADATA_RELAY_TOKEN"] = "fixture-secret"
    os.environ["METADATA_RELAY_ENABLED"] = "true"
    server, thread = _start(module)
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}{module.V0_10_METADATA_RELAY_PATH}",
            headers={"Authorization": "Bearer fixture-secret"},
        )
        with urlopen(request, timeout=5) as response:
            assert response.status == 200
            assert response.headers["X-Qookey-Upstream-Status"] == "200"
            assert response.headers["X-Qookey-Symbol-Count"] == "872"
            assert response.headers["X-Qookey-Raw-Persisted"] == "false"
            assert response.read() == raw_fixture
        assert calls == 1

        old_request = Request(
            f"http://127.0.0.1:{port}{module.METADATA_RELAY_PATH}",
            headers={"Authorization": "Bearer fixture-secret"},
        )
        try:
            urlopen(old_request, timeout=5)
            raise AssertionError("historical V0.7 raw relay unexpectedly enabled")
        except HTTPError as exc:
            assert exc.code == 503
            payload = json.loads(exc.read().decode("utf-8"))
        assert payload["status"] == "DISABLED"
        assert payload["provider_requests_performed"] == 0
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


def test_v010_wrong_secret_stops_before_provider_request() -> None:
    module = _server_module()
    calls = 0

    def forbidden_fetch():
        nonlocal calls
        calls += 1
        raise AssertionError("wrong V0.10 secret reached provider helper")

    module.fetch_exchange_info_raw = forbidden_fetch
    prior = os.environ.get("METADATA_RELAY_TOKEN")
    os.environ["METADATA_RELAY_TOKEN"] = "expected-secret"
    server, thread = _start(module)
    try:
        port = server.server_address[1]
        request = Request(
            f"http://127.0.0.1:{port}{module.V0_10_METADATA_RELAY_PATH}",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        try:
            urlopen(request, timeout=5)
            raise AssertionError("wrong V0.10 secret unexpectedly passed")
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


def test_render_runtime_contains_no_r2_credentials() -> None:
    text = SERVER.read_text(encoding="utf-8")
    for token in (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_ACCOUNT_ID",
        "R2_BUCKET_NAME",
    ):
        assert token not in text


def test_v010_capture_uses_v010_receipt_and_writes_receipt_last_with_fakes() -> None:
    prior_run = os.environ.get("GITHUB_RUN_ID")
    prior_sha = os.environ.get("GITHUB_SHA")
    os.environ["GITHUB_RUN_ID"] = "510510"
    os.environ["GITHUB_SHA"] = "fixture-v010-sha"
    store = FakeStore(initial_sizes=[22_120_404])
    try:
        result = v10.capture_v0_10(
            now=datetime(2026, 8, 27, 0, 17, tzinfo=timezone.utc),
            provider_fetcher=_payloads,
            store_factory=lambda: store,
        )
    finally:
        if prior_run is None:
            os.environ.pop("GITHUB_RUN_ID", None)
        else:
            os.environ["GITHUB_RUN_ID"] = prior_run
        if prior_sha is None:
            os.environ.pop("GITHUB_SHA", None)
        else:
            os.environ["GITHUB_SHA"] = prior_sha

    assert result["status"] == "PASS"
    assert result["stage"] == "PROVIDER_EQUIVALENCE_V0_10_RENDER_METADATA_CAPTURE_PASS"
    assert result["receipt_schema"] == "provider-equivalence-v0-10-render-metadata-capture-receipt-v0.1"
    assert result["capture_execution_version"] == "v0_10"
    assert result["object_count"] == 3
    assert result["r2_writes_performed"] is True
    assert result["holdout_candles_accessed"] is False
    assert store.put_order[-1].endswith("/receipt.json")
    receipt = json.loads(store.objects[store.put_order[-1]].decode("utf-8"))
    assert receipt["schema"] == "provider-equivalence-v0-10-render-metadata-capture-receipt-v0.1"
    assert receipt["stage"] == "PROVIDER_EQUIVALENCE_V0_10_RENDER_METADATA_CAPTURE_PASS"
    assert receipt["capture_execution_version"] == "v0_10"
    assert receipt["transport"]["render_relay_path"] == "/metadata/v0-10/binance-exchange-info"
    assert receipt["authorization_boundary"]["holdout_candle_access_authorized"] is False
    assert "METADATA_RELAY_TOKEN" not in json.dumps(receipt)


def test_v010_r2_headroom_blocks_before_any_write() -> None:
    prior_run = os.environ.get("GITHUB_RUN_ID")
    os.environ["GITHUB_RUN_ID"] = "510511"
    store = FakeStore(initial_sizes=[7_999_999_999])
    try:
        result = v10.capture_v0_10(
            now=datetime(2026, 8, 27, 0, 47, tzinfo=timezone.utc),
            provider_fetcher=_payloads,
            store_factory=lambda: store,
        )
    finally:
        if prior_run is None:
            os.environ.pop("GITHUB_RUN_ID", None)
        else:
            os.environ["GITHUB_RUN_ID"] = prior_run
    assert result["status"] == "BLOCKED"
    assert result["stage"] == "R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE"
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert store.objects == {}


def test_v010_outside_window_stops_before_provider_and_r2() -> None:
    provider_called = False
    store_called = False

    def provider_fetcher():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("outside-window V0.10 reached provider")

    def store_factory():
        nonlocal store_called
        store_called = True
        raise AssertionError("outside-window V0.10 constructed R2")

    result = v10.capture_v0_10(
        now=datetime(2026, 8, 26, 23, 59, tzinfo=timezone.utc),
        provider_fetcher=provider_fetcher,
        store_factory=store_factory,
    )
    assert result["status"] == "SKIP"
    assert result["provider_requests_performed"] == 0
    assert result["r2_client_constructed"] is False
    assert result["r2_writes_performed"] is False
    assert provider_called is False
    assert store_called is False
