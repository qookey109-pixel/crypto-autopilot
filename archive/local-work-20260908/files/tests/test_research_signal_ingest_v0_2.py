from __future__ import annotations

import json
import unittest
from io import BytesIO
from pathlib import Path

from crypto_autopilot.research_signal_ingest_v0_2 import (
    ResearchSignalIngestError,
    build_signal_payload,
    collect_sources,
    fetch_public_source,
    parse_source_payload,
)
from crypto_autopilot.research_signal_layer import ResearchSignalLayerError


def _forecast_row() -> dict[str, object]:
    return {
        "forecast_id": "f-1", "symbol": "BTCUSDT", "direction": "long",
        "confidence": 0.75, "published_at_ms": 1000, "target_time_ms": 2000,
    }


def _parse(row: dict[str, object], **kwargs: object):
    return parse_source_payload(
        source_id="synthetic", source_url="https://example.test/forecast",
        body=json.dumps({"title": "Evidence", "forecasts": [row]}).encode(),
        content_type="application/json", retrieved_at_ms=1500, **kwargs,
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
    def test_metadata_mode_keeps_metadata_but_never_parses_forecasts(self) -> None:
        for row in (_forecast_row(), {"invalid": "forecast"}):
            with self.subTest(row=row):
                snapshot, forecasts = _parse(row, parse_mode="metadata_only")
                self.assertEqual(snapshot.title, "Evidence")
                self.assertEqual(snapshot.status, "PARSED")
                self.assertEqual(snapshot.forecast_count, 0)
                self.assertEqual(len(snapshot.body_sha256), 64)
                self.assertEqual(forecasts, ())

    def test_frozen_source_modes_are_propagated_through_collection(self) -> None:
        config = json.loads((Path(__file__).resolve().parents[1] /
                             "config/research_signal_layer_v0_2.json").read_text())
        calls = []

        def opener(request, **_kwargs):
            calls.append(request.full_url)
            row = {**_forecast_row(), "forecast_id": f"f-{len(calls)}"}
            return _Response(json.dumps({"forecasts": [row]}).encode(), "application/json")

        snapshots, forecasts = collect_sources(
            config["sources"], timeout_seconds=1, max_bytes=1000,
            opener=opener, retrieved_at_ms=1500,
        )
        self.assertEqual(calls, [source["url"] for source in config["sources"]])
        self.assertEqual([s.forecast_count for s in snapshots], [1, 1, 0])
        self.assertEqual([f.source for f in forecasts], ["capafy_category_11", "capafy_btc_cycle_radar"])

    def test_missing_or_invalid_mode_blocks_before_any_source_request(self) -> None:
        def opener(*_args, **_kwargs):
            self.fail("invalid source configuration must not call the opener")

        valid = {"source_id": "valid", "url": "https://example.test/a",
                 "parse_mode": "structured_json_only"}
        for mode in (None, "", "guess_prose", [], True):
            with self.subTest(mode=mode):
                invalid = {"source_id": "invalid", "url": "https://example.test/b"}
                if mode is not None:
                    invalid["parse_mode"] = mode
                with self.assertRaisesRegex(ResearchSignalIngestError, "parse_mode"):
                    collect_sources([valid, invalid], timeout_seconds=1, max_bytes=1000, opener=opener)
                with self.assertRaisesRegex(ResearchSignalIngestError, "parse_mode"):
                    fetch_public_source(source_id="invalid", source_url="https://example.test/b",
                                        timeout_seconds=1, max_bytes=1000, opener=opener, parse_mode=mode)

    def test_publication_time_is_required_without_coercion(self) -> None:
        missing = _forecast_row()
        del missing["published_at_ms"]
        rows = [missing] + [{**_forecast_row(), "published_at_ms": value}
                            for value in (None, True, False, 1000.5, "1000", [], {})]
        for row in rows:
            with self.subTest(row=row):
                with self.assertRaisesRegex(ResearchSignalIngestError, "explicit integer"):
                    _parse(row)

    def test_publication_time_must_obey_existing_temporal_contract(self) -> None:
        for published in (-1, 1501, 2000):
            with self.subTest(published=published):
                with self.assertRaises(ResearchSignalLayerError):
                    _parse({**_forecast_row(), "published_at_ms": published})
        for published in (0, 1000, 1500):
            with self.subTest(published=published):
                _, forecasts = _parse({**_forecast_row(), "published_at_ms": published})
                self.assertEqual(forecasts[0].published_at_ms, published)

    def test_invalid_forecast_discards_whole_source_and_continues_collection(self) -> None:
        def opener(request, **_kwargs):
            rows = [_forecast_row()]
            if request.full_url.endswith("/bad"):
                bad = {**_forecast_row(), "forecast_id": "bad"}
                del bad["published_at_ms"]
                rows.append(bad)
            return _Response(json.dumps({"forecasts": rows}).encode(), "application/json")

        snapshots, forecasts = collect_sources(
            [{"source_id": name, "url": f"https://example.test/{name}",
              "parse_mode": "structured_json_only"} for name in ("bad", "good")],
            timeout_seconds=1, max_bytes=1000, opener=opener, retrieved_at_ms=1500,
        )
        self.assertEqual([s.status for s in snapshots], ["FETCH_FAILED", "PARSED"])
        self.assertEqual([s.forecast_count for s in snapshots], [0, 1])
        self.assertIn("published_at_ms", snapshots[0].error)
        self.assertEqual([f.source for f in forecasts], ["good"])

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
                {"source_id": "ok", "url": "https://example.test/ok", "enabled": True,
                 "parse_mode": "structured_json_only"},
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
