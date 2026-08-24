from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone

from crypto_autopilot.research_signal_quality import (
    ResearchSignalQualityError,
    evaluate_research_signal_quality,
)


NAMESPACE = "research/signal-layer/v0-2"
RUN_ID = "github-123-1"
NOW = datetime(2026, 8, 24, 6, 0, tzinfo=timezone.utc)


def _bytes(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


class FakeStore:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.reads: list[str] = []

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        self.reads.append(key)
        return self.objects.get(key)

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        self.reads.append(key)
        payload = self.objects[key]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("fixture SHA mismatch")
        return payload


def _fixture(*, forecasts: list[dict[str, object]] | None = None) -> FakeStore:
    payload_key = f"{NAMESPACE}/runs/run={RUN_ID}/signals.json"
    manifest_key = f"{NAMESPACE}/runs/run={RUN_ID}/manifest.json"
    latest_key = f"{NAMESPACE}/latest.json"
    payload = _bytes(
        {
            "schema": "research-signal-layer-run-v0.2",
            "status": "PASS",
            "mode": "RESEARCH_ONLY",
            "run_id": RUN_ID,
            "generated_at_utc": "2026-08-24T05:30:00Z",
            "source_snapshots": [
                {
                    "source_id": "capafy",
                    "status": "PARSED",
                    "retrieved_at_ms": 1_777_182_600_000,
                }
            ],
            "kol_forecasts": forecasts or [],
            "authority": {
                "external_source_fetch": True,
                "production_r2_write": True,
                "automatic_model_promotion": False,
                "direct_trade_trigger": False,
                "real_money_order": False,
                "live_trading": False,
            },
        }
    )
    manifest = _bytes(
        {
            "schema": "research-signal-layer-manifest-v0.2",
            "run_id": RUN_ID,
            "payload_key": payload_key,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
    )
    latest = _bytes(
        {
            "schema": "research-signal-layer-latest-v0.2",
            "run_id": RUN_ID,
            "manifest_key": manifest_key,
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "generated_at_utc": "2026-08-24T05:30:00Z",
        }
    )
    return FakeStore({latest_key: latest, manifest_key: manifest, payload_key: payload})


class ResearchSignalQualityTests(unittest.TestCase):
    def test_metadata_only_signal_is_valid_and_read_only(self) -> None:
        store = _fixture()
        report = evaluate_research_signal_quality(store, namespace=NAMESPACE, now=NOW)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["quality"], "METADATA_ONLY")
        self.assertEqual(report["forecast_count"], 0)
        self.assertFalse(report["authority"]["r2_list"])
        self.assertFalse(report["authority"]["r2_write"])
        self.assertFalse(report["authority"]["direct_trade_trigger"])
        self.assertEqual(len(store.reads), 3)

    def test_structured_forecast_is_reported_ready(self) -> None:
        forecast = {
            "forecast_id": "f-1",
            "source": "capafy",
            "source_url": "https://example.test/forecast",
            "symbol": "BTCUSDT",
            "direction": "long",
            "confidence": 0.75,
            "published_at_ms": 1_777_182_000_000,
            "target_time_ms": 1_777_268_400_000,
            "ingested_at_ms": 1_777_182_600_000,
            "content_sha256": "a" * 64,
        }
        report = evaluate_research_signal_quality(
            _fixture(forecasts=[forecast]), namespace=NAMESPACE, now=NOW
        )
        self.assertEqual(report["quality"], "FORECAST_READY")
        self.assertEqual(report["forecast_count"], 1)

    def test_manifest_sha_mismatch_fails_closed(self) -> None:
        store = _fixture()
        latest_key = f"{NAMESPACE}/latest.json"
        latest = json.loads(store.objects[latest_key])
        latest["manifest_sha256"] = "0" * 64
        store.objects[latest_key] = _bytes(latest)
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            evaluate_research_signal_quality(store, namespace=NAMESPACE, now=NOW)

    def test_future_payload_fails_closed(self) -> None:
        store = _fixture()
        latest_key = f"{NAMESPACE}/latest.json"
        latest = json.loads(store.objects[latest_key])
        manifest_key = latest["manifest_key"]
        manifest = json.loads(store.objects[manifest_key])
        payload_key = manifest["payload_key"]
        payload = json.loads(store.objects[payload_key])
        payload["generated_at_utc"] = "2026-08-25T05:30:00Z"
        latest["generated_at_utc"] = payload["generated_at_utc"]
        store.objects[payload_key] = _bytes(payload)
        manifest["payload_sha256"] = hashlib.sha256(store.objects[payload_key]).hexdigest()
        store.objects[manifest_key] = _bytes(manifest)
        latest["manifest_sha256"] = hashlib.sha256(store.objects[manifest_key]).hexdigest()
        store.objects[latest_key] = _bytes(latest)
        with self.assertRaisesRegex(ResearchSignalQualityError, "future"):
            evaluate_research_signal_quality(store, namespace=NAMESPACE, now=NOW)

    def test_stale_payload_is_an_explicit_alert(self) -> None:
        report = evaluate_research_signal_quality(
            _fixture(),
            namespace=NAMESPACE,
            now=datetime(2026, 8, 26, 6, 0, tzinfo=timezone.utc),
            max_age_seconds=129_600,
        )
        self.assertEqual(report["status"], "ALERT")
        self.assertEqual(report["lineage"], "PASS")


if __name__ == "__main__":
    unittest.main()
