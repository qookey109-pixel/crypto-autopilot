from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture import (
    ContextForwardCaptureError,
    ContextForwardCaptureNotAuthorized,
    build_context_forward_snapshot,
    prepared_collect_context_forward_snapshot,
    validate_context_forward_capture_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "context_forward_capture_v0_1.json"
SOURCE_LINEAGE_PATH = ROOT / "config" / "context_source_lineage_v0_1.json"


def _load_contract() -> tuple[dict[str, object], bytes]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source_bytes = SOURCE_LINEAGE_PATH.read_bytes()
    return config, source_bytes


def _global_payload(*, last_updated: int = 1_788_451_000) -> bytes:
    return json.dumps(
        {
            "market_cap_usd": 3_000_000_000_000,
            "bitcoin_dominance_percentage": 50.0,
            "last_updated": last_updated,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _eth_payload(*, last_updated: str = "2026-09-04T02:10:00Z", market_cap: float = 400_000_000_000) -> bytes:
    return json.dumps(
        {
            "id": "eth-ethereum",
            "symbol": "ETH",
            "last_updated": last_updated,
            "quotes": {"USD": {"market_cap": market_cap}},
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class ContextForwardCaptureV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config, self.source_bytes = _load_contract()
        # 2026-09-04T02:15:00Z
        self.capture_ms = 1_788_451_300_000

    def test_frozen_config_validates_against_exact_source_lineage(self) -> None:
        validate_context_forward_capture_config(
            self.config, source_lineage_bytes=self.source_bytes
        )
        expected = hashlib.sha256(self.source_bytes).hexdigest()
        self.assertEqual(self.config["source_lineage"]["sha256"], expected)

    def test_builds_same_provider_total3_snapshot_and_hashes_raw_payloads(self) -> None:
        global_payload = _global_payload()
        eth_payload = _eth_payload()
        snapshot = build_context_forward_snapshot(
            config=self.config,
            source_lineage_bytes=self.source_bytes,
            global_payload=global_payload,
            eth_payload=eth_payload,
            capture_timestamp_ms=self.capture_ms,
        )

        self.assertEqual(snapshot.schema, "context-forward-snapshot-v0.1")
        self.assertEqual(snapshot.provider, "coinpaprika")
        self.assertAlmostEqual(snapshot.total_market_cap_usd, 3_000_000_000_000)
        self.assertAlmostEqual(snapshot.btc_market_cap_usd, 1_500_000_000_000)
        self.assertAlmostEqual(snapshot.eth_market_cap_usd, 400_000_000_000)
        self.assertAlmostEqual(snapshot.total3_value, 1_100_000_000_000)
        self.assertEqual(snapshot.global_provider_age_ms, 300_000)
        self.assertEqual(snapshot.eth_provider_age_ms, 300_000)
        self.assertEqual(snapshot.provider_component_skew_ms, 0)
        self.assertEqual(
            snapshot.global_raw_payload_sha256, hashlib.sha256(global_payload).hexdigest()
        )
        self.assertEqual(
            snapshot.eth_raw_payload_sha256, hashlib.sha256(eth_payload).hexdigest()
        )
        self.assertTrue(snapshot.forward_only)
        self.assertFalse(snapshot.historical_backfill_claim)
        self.assertFalse(snapshot.authority)

    def test_provider_execution_rejects_before_first_transport_call(self) -> None:
        calls: list[str] = []

        def transport(url: str) -> bytes:
            calls.append(url)
            raise AssertionError("transport must not be called")

        with self.assertRaises(ContextForwardCaptureNotAuthorized):
            prepared_collect_context_forward_snapshot(
                config=self.config,
                source_lineage_bytes=self.source_bytes,
                transport=transport,
                capture_timestamp_ms=self.capture_ms,
            )
        self.assertEqual(calls, [])

    def test_future_provider_timestamp_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "cannot be in the future"):
            build_context_forward_snapshot(
                config=self.config,
                source_lineage_bytes=self.source_bytes,
                global_payload=_global_payload(last_updated=1_788_451_301),
                eth_payload=_eth_payload(),
                capture_timestamp_ms=self.capture_ms,
            )

    def test_stale_provider_timestamp_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "too stale"):
            build_context_forward_snapshot(
                config=self.config,
                source_lineage_bytes=self.source_bytes,
                global_payload=_global_payload(last_updated=1_788_450_000),
                eth_payload=_eth_payload(),
                capture_timestamp_ms=self.capture_ms,
            )

    def test_component_skew_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "too far apart"):
            build_context_forward_snapshot(
                config=self.config,
                source_lineage_bytes=self.source_bytes,
                global_payload=_global_payload(last_updated=1_788_450_650),
                eth_payload=_eth_payload(last_updated="2026-09-04T02:15:00Z"),
                capture_timestamp_ms=self.capture_ms,
            )

    def test_nonpositive_total3_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "total3_value"):
            build_context_forward_snapshot(
                config=self.config,
                source_lineage_bytes=self.source_bytes,
                global_payload=_global_payload(),
                eth_payload=_eth_payload(market_cap=1_600_000_000_000),
                capture_timestamp_ms=self.capture_ms,
            )

    def test_duplicate_json_keys_fail_closed(self) -> None:
        duplicate = (
            b'{"market_cap_usd":3000000000000,'
            b'"bitcoin_dominance_percentage":50,'
            b'"last_updated":1788451000,"last_updated":1788451000}'
        )
        with self.assertRaisesRegex(ContextForwardCaptureError, "duplicate key"):
            build_context_forward_snapshot(
                config=self.config,
                source_lineage_bytes=self.source_bytes,
                global_payload=duplicate,
                eth_payload=_eth_payload(),
                capture_timestamp_ms=self.capture_ms,
            )

    def test_source_lineage_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "SHA-256 mismatch"):
            validate_context_forward_capture_config(
                self.config, source_lineage_bytes=self.source_bytes + b"\n"
            )


if __name__ == "__main__":
    unittest.main()
