from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from crypto_autopilot import provider_metadata_capture_v0_10 as v10
from crypto_autopilot import provider_metadata_capture_v0_8_successor as successor


def _pionex_payload(symbols: list[str]) -> bytes:
    return json.dumps(
        {
            "result": True,
            "data": {
                "symbols": [
                    {
                        "symbol": symbol,
                        "quoteStep": "0.01",
                        "status": "TRADING",
                        "contractType": "PERPETUAL",
                    }
                    for symbol in symbols
                ]
            },
        }
    ).encode("utf-8")


def _binance_payload(symbols: list[str]) -> bytes:
    return json.dumps(
        {
            "symbols": [
                {
                    "symbol": symbol,
                    "status": "TRADING",
                    "contractType": "PERPETUAL",
                    "filters": [
                        {"filterType": "PRICE_FILTER", "tickSize": "0.01"}
                    ],
                }
                for symbol in symbols
            ]
        }
    ).encode("utf-8")


def test_pionex_endpoint_adds_only_explicit_perp_market_type() -> None:
    url = v10._pionex_perp_endpoint("https://api.pionex.com/api/v1/common/symbols")
    parsed = urlsplit(url)

    assert parsed.scheme == "https"
    assert parsed.netloc == "api.pionex.com"
    assert parsed.path == "/api/v1/common/symbols"
    assert parse_qs(parsed.query) == {"type": ["PERP"]}


def test_pionex_endpoint_rejects_conflicting_market_type() -> None:
    with pytest.raises(RuntimeError, match="conflicting market type"):
        v10._pionex_perp_endpoint(
            "https://api.pionex.com/api/v1/common/symbols?type=SPOT"
        )


def test_v010_provider_fetch_explicitly_requests_perp(monkeypatch) -> None:
    _, _, pionex_symbols, binance_symbols = (
        successor.validate_prepared_runtime_authorities()
    )
    observed_urls: list[str] = []

    def fake_pionex_fetch(url: str, *, max_bytes: int):
        observed_urls.append(url)
        assert max_bytes == 2_097_152
        assert parse_qs(urlsplit(url).query) == {"type": ["PERP"]}
        return _pionex_payload(pionex_symbols), "application/json"

    def fake_binance_fetch(*, url: str, max_bytes: int):
        assert url == v10.V0_10_RENDER_RELAY_URL
        assert max_bytes == 8_000_000
        return _binance_payload(binance_symbols), "application/json"

    monkeypatch.setattr(v10.v02, "_fetch_json_bytes", fake_pionex_fetch)
    monkeypatch.setattr(v10.successor, "_fetch_render_relay_raw", fake_binance_fetch)

    pionex, binance, _ = v10.fetch_v0_10_provider_payloads()

    assert len(observed_urls) == 1
    assert len(pionex.vector) == 15
    assert len(binance.vector) == 15
    assert all(row["contract_type"] == "PERPETUAL" for row in pionex.vector)
    assert all(row["contract_type"] == "PERPETUAL" for row in binance.vector)
