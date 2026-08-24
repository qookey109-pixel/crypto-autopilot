from __future__ import annotations

import json
import unittest
from io import BytesIO

from crypto_autopilot.research_signal_ingest_v0_2 import (
    build_signal_payload,
    collect_sources,
    parse_source_payload,
)


class _Response:
    status = 200

    def __init__(self, body: bytes, content_type: str) -> None:
        self.headers = {"Content-Type": content_type}
        self._body = BytesIO(body)

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class ResearchSignalIngestTests(unittest.TestCase):
    def test_structured_forecast_is_accepted(self) -> None:
        body = json.dumps(
            {
                "title": "BTC cycle",
                "forecasts": [
                    {
                        "forecast_id": "f-1",
                        "symbol": "BTCUSDT",
                        "direction": "long",
                        "confidence": 0.75,
                        "published_at_ms": 1_000,
                        "target_time_ms": 2_000,
                    }
                ],
            }
        ).encode()
        snapshot, forecasts = parse_source_payload(
            source_id="capafy",
            source_url="https://example.test/forecast",
            body=body,
            content_type="application/json",
            retrieved_at_ms=1_500,
        )
        self.assertEqual(snapshot.forecast_count, 1)
        self.assertEqual(forecasts[0].direction, "long")
        self.assertEqual(forecasts[0].content_sha256, snapshot.body_sha256)

    def test_html_prose_is_metadata_only_and_does_not_guess_direction(self) -> None:
        snapshot, forecasts = parse_source_payload(
            source_id="x-profile",
            source_url="https://example.test/profile",
            body=b'<html><meta property="og:title" content="BTC outlook"><p>bullish</p></html>',
            content_type="text/html",
            retrieved_at_ms=1_500,
        )
        self.assertEqual(snapshot.title, "BTC outlook")
        self.assertEqual(forecasts, ())

    def test_collection_skips_disabled_sources_and_retains_fetch_failures(self) -> None:
        def opener(*_args: object, **_kwargs: object) -> _Response:
            return _Response(b'{"title":"ok"}', "application/json")

        snapshots, forecasts = collect_sources(
            [
                {"source_id": "disabled", "url": "https://example.test/no", "enabled": False},
                {"source_id": "ok", "url": "https://example.test/ok", "enabled": True},
            ],
            timeout_seconds=1,
            max_bytes=1000,
            opener=opener,
            retrieved_at_ms=1_500,
        )
        self.assertEqual([item.source_id for item in snapshots], ["ok"])
        self.assertEqual(forecasts, ())

    def test_payload_is_explicitly_research_only(self) -> None:
        payload = build_signal_payload(
            run_id="run-1",
            generated_at_utc="2026-08-24T00:00:00Z",
            snapshots=(),
            forecasts=(),
        )
        self.assertEqual(payload["mode"], "RESEARCH_ONLY")
        self.assertFalse(payload["authority"]["direct_trade_trigger"])
        self.assertFalse(payload["authority"]["automatic_model_promotion"])


if __name__ == "__main__":
    unittest.main()
