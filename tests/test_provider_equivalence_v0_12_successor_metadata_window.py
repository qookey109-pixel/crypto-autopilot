from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from crypto_autopilot import provider_metadata_capture_v0_2 as v02
from crypto_autopilot import provider_metadata_capture_v0_12 as v12
from crypto_autopilot.storage.r2 import R2ObjectReceipt

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json"
AUTHORITY = (
    ROOT
    / "research/receipts/"
    "2026-08-31-provider-equivalence-v0-12-successor-metadata-window-authority.json"
)
BINDING = (
    ROOT / "config/provider_equivalence_v0_12_successor_metadata_window_binding_v0_1.json"
)
BINDING_RECEIPT = (
    ROOT
    / "research/receipts/"
    "2026-08-31-provider-equivalence-v0-12-successor-metadata-window-binding.json"
)
V010_WORKFLOW = (
    ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
)
V012_WORKFLOW = (
    ROOT / ".github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml"
)


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


def _pionex_payload(*, legacy: bool) -> bytes:
    rows = []
    for index in range(15):
        row: dict[str, object] = {
            "symbol": f"P{index:02d}_USDT_PERP",
            "quoteStep": "0.01",
        }
        if legacy:
            row.update({"type": "PERP", "enable": True})
        else:
            row.update({"contractType": "PERPETUAL", "status": "TRADING"})
        rows.append(row)
    return json.dumps({"result": True, "data": {"symbols": rows}}).encode()


def _vector(prefix: str) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "symbol": f"{prefix}{index:02d}",
            "price_increment": "0.01",
            "status": "TRADING",
            "contract_type": "PERPETUAL",
            "source_field": "fixture",
        }
        for index in range(15)
    )


def _payloads() -> tuple[v02.ProviderPayload, v02.ProviderPayload, dict[str, object]]:
    cfg, _ = v12.validate_successor_authority()
    pionex = v02.ProviderPayload(
        provider="pionex",
        raw=b'{"fixture":"pionex-v012"}',
        content_type="application/json",
        vector=_vector("P"),
    )
    binance = v02.ProviderPayload(
        provider="binance_usdm",
        raw=b'{"fixture":"binance-v012"}',
        content_type="application/json",
        vector=_vector("B"),
    )
    return pionex, binance, cfg


def _cron_values(field: str, lower: int, upper: int) -> set[int]:
    if field == "*":
        return set(range(lower, upper + 1))
    values: set[int] = set()
    for item in field.split(","):
        if "-" in item:
            start, end = item.split("-", 1)
            values.update(range(int(start), int(end) + 1))
        else:
            values.add(int(item))
    assert values and min(values) >= lower and max(values) <= upper
    return values


def _matches(cron: str, instant: datetime) -> bool:
    minute, hour, day, month, weekday = cron.split()
    assert weekday == "*"
    return (
        instant.minute in _cron_values(minute, 0, 59)
        and instant.hour in _cron_values(hour, 0, 23)
        and instant.day in _cron_values(day, 1, 31)
        and instant.month in _cron_values(month, 1, 12)
    )


def test_authority_is_atomic_free_only_and_downstream_closed() -> None:
    cfg, authority = v12.validate_successor_authority()
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    binding_receipt = json.loads(BINDING_RECEIPT.read_text(encoding="utf-8"))
    assert cfg["lineage"]["pre_change_main_sha"] == (
        "a6c2f0748a2b352f1ccac1fc349bbd4e0b3b80d4"
    )
    assert cfg["lineage"]["protected_main_pr_number"] == 0
    assert cfg["lineage"]["minimum_operational_change_commit_sha"] is None
    assert authority["effectivity"]["protected_main_pr_number"] == 0
    assert authority["effectivity"]["minimum_operational_change_commit_sha"] is None
    assert binding["lineage"]["protected_main_pr_number"] == 212
    assert binding["lineage"]["minimum_operational_change_commit_sha"] == (
        "80732edee9a8954b53b4b56115ecb0d506591f0a"
    )
    assert binding_receipt["lineage"]["protected_main_pr_number"] == 212
    assert binding_receipt["lineage"]["minimum_operational_change_commit_sha"] == (
        binding["lineage"]["minimum_operational_change_commit_sha"]
    )
    assert cfg["atomic_schedule_transition"][
        "concurrent_v0_10_and_v0_12_capture_paths_authorized"
    ] is False
    assert cfg["render_transport"]["monthly_budget_usd"] == 0
    assert cfg["render_transport"]["render_receives_r2_credentials"] is False
    assert cfg["storage"]["free_only_operational_hard_stop_bytes"] == 8_000_000_000
    assert cfg["frozen_future_stability_contract"]["partial_window_may_produce_pass"] is False
    assert cfg["frozen_future_stability_contract"][
        "production_r2_evaluation_authorized_now"
    ] is False
    boundary = cfg["authorization_boundary"]
    assert boundary["v0_12_metadata_capture_execution_authorized_on_main_merge"] is True
    assert boundary["v0_12_metadata_only_r2_writes_authorized_on_main_merge"] is True
    for key, value in boundary.items():
        if key.startswith("v0_12_metadata"):
            continue
        assert value is False, key


def test_atomic_schedule_transition_has_exact_194_slots_and_no_v010_cron() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    v010 = V010_WORKFLOW.read_text(encoding="utf-8").splitlines()
    v012 = V012_WORKFLOW.read_text(encoding="utf-8").splitlines()
    assert not any(line == "  schedule:" for line in v010)
    assert any(line == "  schedule:" for line in v012)

    crons = cfg["atomic_schedule_transition"]["successor_cron_utc"]
    assert crons == [
        "17,47 2-23 4 9 *",
        "17,47 * 5,6,7,8,9,10,11 9 *",
        "17,47 0-3 12 9 *",
    ]
    expected_lines = {f'    - cron: "{cron}"' for cron in crons}
    assert expected_lines.issubset(set(v012))

    start = datetime(2026, 9, 4, 2, tzinfo=timezone.utc)
    final_attempt = datetime(2026, 9, 12, 3, 47, tzinfo=timezone.utc)
    cursor = start
    attempts: list[datetime] = []
    while cursor <= final_attempt:
        if any(_matches(cron, cursor) for cron in crons):
            attempts.append(cursor)
        cursor += timedelta(minutes=1)
    assert len(attempts) == 388
    assert {attempt.minute for attempt in attempts} == {17, 47}
    assert len({attempt.replace(minute=0) for attempt in attempts}) == 194


def test_pionex_parser_accepts_documented_new_and_legacy_contracts() -> None:
    symbols = tuple(f"P{index:02d}_USDT_PERP" for index in range(15))
    modern = v12.parse_pionex_perp_symbols(_pionex_payload(legacy=False), symbols)
    legacy = v12.parse_pionex_perp_symbols(_pionex_payload(legacy=True), symbols)
    assert len(modern) == len(legacy) == 15
    assert all(row["status"] == "TRADING" for row in modern + legacy)
    assert all(row["contract_type"] == "PERPETUAL" for row in modern + legacy)
    assert all("contractType" in row["source_field"] for row in modern)
    assert all("contract=type" in row["source_field"] for row in legacy)


@pytest.mark.parametrize(
    "row_update,error",
    [
        ({"contractType": "PERPETUAL", "type": "SPOT", "status": "TRADING"}, "type invalid"),
        ({"contractType": "PERPETUAL", "status": "TRADING", "enable": False}, "disagree"),
        ({"quoteStep": "0.01", "status": "TRADING"}, "contractType/type missing"),
        ({"quoteStep": "0.01", "type": "PERP"}, "status/enable missing"),
    ],
)
def test_pionex_parser_fails_closed_on_unknown_missing_or_conflicting_fields(
    row_update: dict[str, object], error: str
) -> None:
    row = {"symbol": "BTC_USDT_PERP", "quoteStep": "0.01"}
    row.update(row_update)
    raw = json.dumps({"result": True, "data": {"symbols": [row]}}).encode()
    with pytest.raises(RuntimeError, match=error):
        v12.parse_pionex_perp_symbols(raw, ("BTC_USDT_PERP",))


def test_v012_capture_writes_receipt_last_and_preserves_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setenv("GITHUB_RUN_ID", "120012")
    monkeypatch.setenv("GITHUB_SHA", "fixture-v012-sha")
    store = FakeStore(initial_sizes=[22_120_404])
    result = v12.capture_v0_12(
        now=datetime(2026, 9, 4, 2, 17, tzinfo=timezone.utc),
        provider_fetcher=_payloads,
        store_factory=lambda: store,
    )

    assert result["status"] == "PASS"
    assert result["stage"] == v12.V0_12_CAPTURE_PASS_STAGE
    assert result["capture_execution_version"] == "v0_12"
    assert result["object_count"] == 3
    assert result["r2_writes_performed"] is True
    assert result["holdout_candles_accessed"] is False
    assert store.put_order[-1].endswith("/receipt.json")
    receipt = json.loads(store.objects[store.put_order[-1]].decode("utf-8"))
    assert receipt["schema"] == v12.V0_12_RECEIPT_SCHEMA
    assert receipt["capture_execution_version"] == "v0_12"
    assert receipt["transport"]["render_relay_path"] == (
        "/metadata/v0-10/binance-exchange-info"
    )
    assert receipt["authorization_boundary"]["v0_10_replay_or_backfill_authorized"] is False
    assert receipt["authorization_boundary"]["holdout_candle_access_authorized"] is False
    assert "METADATA_RELAY_TOKEN" not in json.dumps(receipt)


def test_v012_outside_window_stops_before_provider_and_r2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    provider_called = False
    store_called = False

    def provider_fetcher():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("outside-window V0.12 reached provider")

    def store_factory():
        nonlocal store_called
        store_called = True
        raise AssertionError("outside-window V0.12 constructed R2")

    result = v12.capture_v0_12(
        now=datetime(2026, 9, 4, 1, 59, tzinfo=timezone.utc),
        provider_fetcher=provider_fetcher,
        store_factory=store_factory,
    )
    assert result["status"] == "SKIP"
    assert result["provider_requests_performed"] == 0
    assert result["r2_client_constructed"] is False
    assert result["r2_writes_performed"] is False
    assert provider_called is False
    assert store_called is False


def test_v012_manual_event_stops_before_provider_and_r2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    provider_called = False
    store_called = False

    def provider_fetcher():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("manual V0.12 event reached provider")

    def store_factory():
        nonlocal store_called
        store_called = True
        raise AssertionError("manual V0.12 event constructed R2")

    result = v12.capture_v0_12(
        now=datetime(2026, 9, 4, 2, 17, tzinfo=timezone.utc),
        provider_fetcher=provider_fetcher,
        store_factory=store_factory,
    )
    assert result["status"] == "SKIP"
    assert result["stage"] == "V0_12_SUCCESSOR_METADATA_CAPTURE_SCHEDULE_EVENT_REQUIRED"
    assert result["provider_requests_performed"] == 0
    assert result["r2_client_constructed"] is False
    assert result["r2_writes_performed"] is False
    assert provider_called is False
    assert store_called is False


def test_v012_r2_headroom_blocks_before_any_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setenv("GITHUB_RUN_ID", "120013")
    store = FakeStore(initial_sizes=[7_999_999_999])
    result = v12.capture_v0_12(
        now=datetime(2026, 9, 4, 2, 47, tzinfo=timezone.utc),
        provider_fetcher=_payloads,
        store_factory=lambda: store,
    )
    assert result["status"] == "BLOCKED"
    assert result["r2_writes_performed"] is False
    assert store.objects == {}
