from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from crypto_autopilot import provider_metadata_capture_v0_2 as v02
from crypto_autopilot import provider_metadata_capture_v0_8_successor as successor
from crypto_autopilot.storage.r2 import R2ObjectReceipt


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
    p = v02.ProviderPayload(
        provider="pionex",
        raw=b'{"fixture":"pionex"}',
        content_type="application/json",
        vector=_vector("P"),
    )
    b = v02.ProviderPayload(
        provider="binance_usdm",
        raw=b'{"fixture":"binance"}',
        content_type="application/json",
        vector=_vector("B"),
    )
    return p, b, protocol


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


def test_public_successor_entrypoint_is_hard_disabled_before_provider_or_r2_access() -> None:
    provider_called = False
    store_called = False

    def provider_fetcher():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("hard-disabled public entrypoint reached provider")

    def store_factory():
        nonlocal store_called
        store_called = True
        raise AssertionError("hard-disabled public entrypoint constructed R2")

    result = successor.execute_successor_capture(
        now=datetime(2026, 8, 27, 0, 17, tzinfo=timezone.utc),
        provider_fetcher=provider_fetcher,
        store_factory=store_factory,
    )
    assert successor.SUCCESSOR_RUNTIME_EXECUTION_AUTHORIZED is False
    assert result["status"] == "SKIP"
    assert result["stage"] == "V0_8_SUCCESSOR_RUNTIME_EXECUTION_NOT_AUTHORIZED"
    assert result["provider_requests_performed"] == 0
    assert result["render_relay_requests_performed"] == 0
    assert result["r2_client_constructed"] is False
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert provider_called is False
    assert store_called is False


def test_authorized_core_can_complete_with_fakes_without_production_access() -> None:
    prior_run = os.environ.get("GITHUB_RUN_ID")
    prior_sha = os.environ.get("GITHUB_SHA")
    os.environ["GITHUB_RUN_ID"] = "424242"
    os.environ["GITHUB_SHA"] = "fixture-sha"
    store = FakeStore(initial_sizes=[22_120_404])
    try:
        result = successor._execute_successor_capture_authorized(  # noqa: SLF001
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
    assert result["stage"] == "PROVIDER_EQUIVALENCE_V0_8_RENDER_METADATA_CAPTURE_PASS"
    assert result["object_count"] == 3
    assert result["postwrite_sha256_verification"] is True
    assert result["prewrite_r2_bucket_bytes"] == 22_120_404
    assert result["r2_hard_stop_bytes"] == 8_000_000_000
    assert result["r2_writes_performed"] is True
    assert result["r2_deletes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["source_switch_authorized"] is False
    assert result["live_trading_authorized"] is False
    assert len(store.objects) == 3
    assert all(
        key.startswith("metadata/provider-equivalence/v0_7/render-forward-holdout-20260828/")
        for key in store.objects
    )
    assert store.put_order[-1].endswith("/receipt.json")
    receipt = json.loads(store.objects[store.put_order[-1]].decode("utf-8"))
    assert receipt["transport"]["binance_usdm"] == "render_free_web_service"
    assert receipt["authorization_boundary"]["holdout_candle_access_authorized"] is False
    assert "METADATA_RELAY_TOKEN" not in json.dumps(receipt)


def test_authorized_core_free_only_headroom_blocks_before_any_write() -> None:
    prior_run = os.environ.get("GITHUB_RUN_ID")
    os.environ["GITHUB_RUN_ID"] = "424243"
    store = FakeStore(initial_sizes=[7_999_999_999])
    try:
        result = successor._execute_successor_capture_authorized(  # noqa: SLF001
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
    assert result["r2_client_constructed"] is True
    assert result["r2_writes_performed"] is False
    assert result["holdout_candles_accessed"] is False
    assert store.objects == {}


def test_authorized_core_outside_window_stops_before_provider_and_r2_access() -> None:
    provider_called = False
    store_called = False

    def provider_fetcher():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("outside-window run reached provider")

    def store_factory():
        nonlocal store_called
        store_called = True
        raise AssertionError("outside-window run constructed R2")

    result = successor._execute_successor_capture_authorized(  # noqa: SLF001
        now=datetime(2026, 8, 26, 23, 59, tzinfo=timezone.utc),
        provider_fetcher=provider_fetcher,
        store_factory=store_factory,
    )
    assert result["status"] == "SKIP"
    assert result["provider_requests_performed"] == 0
    assert result["r2_client_constructed"] is False
    assert provider_called is False
    assert store_called is False


def test_prepared_authorities_keep_all_execution_gates_closed() -> None:
    _, v07, _, _ = successor.validate_prepared_runtime_authorities()
    boundary = v07["execution_boundary"]
    assert successor.SUCCESSOR_RUNTIME_EXECUTION_AUTHORIZED is False
    assert boundary["render_metadata_relay_enablement_authorized"] is False
    assert boundary["render_metadata_capture_execution_authorized"] is False
    assert boundary["scheduled_capture_activation_authorized"] is False
    assert boundary["metadata_only_r2_writes_authorized_by_this_protocol"] is False
    assert boundary["holdout_candle_access_authorized"] is False
    assert boundary["source_switch_authorized"] is False
    assert boundary["live_trading_authorized"] is False
