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
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "context_forward_capture_v0_1.json"
SOURCE_LINEAGE_PATH = ROOT / "config" / "context_source_lineage_v0_1.json"
CAPTURE_MS = 1_700_000_000_000


def _config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _source_lineage_bytes() -> bytes:
    return SOURCE_LINEAGE_PATH.read_bytes()


def _global_payload(
    *,
    market_cap_usd: float = 2_000_000_000_000,
    dominance: float = 50.0,
    last_updated: int = 1_699_999_700,
) -> bytes:
    return json.dumps(
        {
            "market_cap_usd": market_cap_usd,
            "bitcoin_dominance_percentage": dominance,
            "last_updated": last_updated,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _eth_payload(
    *,
    market_cap_usd: float = 300_000_000_000,
    last_updated: str = "2023-11-14T22:08:40Z",
    coin_id: str = "eth-ethereum",
    symbol: str = "ETH",
) -> bytes:
    return json.dumps(
        {
            "id": coin_id,
            "symbol": symbol,
            "last_updated": last_updated,
            "quotes": {"USD": {"market_cap": market_cap_usd}},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class ContextForwardCaptureTests(unittest.TestCase):
    def test_builds_deterministic_snapshot_and_exact_raw_payload_hashes(self) -> None:
        global_payload = _global_payload()
        eth_payload = _eth_payload()

        first = build_context_forward_snapshot(
            config=_config(),
            source_lineage_bytes=_source_lineage_bytes(),
            global_payload=global_payload,
            eth_payload=eth_payload,
            capture_timestamp_ms=CAPTURE_MS,
        )
        second = build_context_forward_snapshot(
            config=_config(),
            source_lineage_bytes=_source_lineage_bytes(),
            global_payload=global_payload,
            eth_payload=eth_payload,
            capture_timestamp_ms=CAPTURE_MS,
        )

        self.assertEqual(first, second)
        self.assertEqual(first.schema, "context-forward-snapshot-v0.1")
        self.assertEqual(first.provider, "coinpaprika")
        self.assertEqual(first.total_market_cap_usd, 2_000_000_000_000)
        self.assertEqual(first.btc_market_cap_usd, 1_000_000_000_000)
        self.assertEqual(first.eth_market_cap_usd, 300_000_000_000)
        self.assertEqual(first.total3_value, 700_000_000_000)
        self.assertEqual(
            first.global_raw_payload_sha256, hashlib.sha256(global_payload).hexdigest()
        )
        self.assertEqual(first.eth_raw_payload_sha256, hashlib.sha256(eth_payload).hexdigest())
        self.assertFalse(first.authority)
        self.assertFalse(first.historical_backfill_claim)

    def test_prepared_transport_refuses_before_first_provider_request(self) -> None:
        calls: list[str] = []

        def transport(url: str) -> bytes:
            calls.append(url)
            return b"{}"

        with self.assertRaisesRegex(
            ContextForwardCaptureNotAuthorized, "provider execution is not authorized"
        ):
            prepared_collect_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                transport=transport,
                capture_timestamp_ms=CAPTURE_MS,
            )

        self.assertEqual(calls, [])

    def test_future_provider_timestamp_fails_closed(self) -> None:
        future_global = _global_payload(last_updated=(CAPTURE_MS // 1000) + 1)
        with self.assertRaisesRegex(ContextForwardCaptureError, "cannot be in the future"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=future_global,
                eth_payload=_eth_payload(),
                capture_timestamp_ms=CAPTURE_MS,
            )

    def test_stale_provider_timestamp_fails_closed(self) -> None:
        stale_global = _global_payload(last_updated=(CAPTURE_MS // 1000) - 901)
        with self.assertRaisesRegex(ContextForwardCaptureError, "too stale"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=stale_global,
                eth_payload=_eth_payload(),
                capture_timestamp_ms=CAPTURE_MS,
            )

    def test_component_timestamp_skew_above_ten_minutes_fails_closed(self) -> None:
        global_payload = _global_payload(last_updated=(CAPTURE_MS // 1000) - 100)
        eth_payload = _eth_payload(last_updated="2023-11-14T22:00:00Z")
        with self.assertRaisesRegex(ContextForwardCaptureError, "too far apart"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=global_payload,
                eth_payload=eth_payload,
                capture_timestamp_ms=CAPTURE_MS,
            )

    def test_wrong_eth_identity_or_missing_usd_quote_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "identity mismatch"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=_global_payload(),
                eth_payload=_eth_payload(coin_id="btc-bitcoin", symbol="BTC"),
                capture_timestamp_ms=CAPTURE_MS,
            )

        missing_quote = json.dumps(
            {
                "id": "eth-ethereum",
                "symbol": "ETH",
                "last_updated": "2023-11-14T22:08:40Z",
                "quotes": {},
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        with self.assertRaisesRegex(ContextForwardCaptureError, "quotes.USD is required"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=_global_payload(),
                eth_payload=missing_quote,
                capture_timestamp_ms=CAPTURE_MS,
            )

    def test_nonpositive_total3_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContextForwardCaptureError, "total3_value"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=_global_payload(market_cap_usd=100.0, dominance=90.0),
                eth_payload=_eth_payload(market_cap_usd=20.0),
                capture_timestamp_ms=CAPTURE_MS,
            )

    def test_duplicate_json_keys_fail_closed(self) -> None:
        duplicate_global = (
            b'{"market_cap_usd":2000000000000,"market_cap_usd":1,'
            b'"bitcoin_dominance_percentage":50,"last_updated":1699999700}'
        )
        with self.assertRaisesRegex(ContextForwardCaptureError, "duplicate key"):
            build_context_forward_snapshot(
                config=_config(),
                source_lineage_bytes=_source_lineage_bytes(),
                global_payload=duplicate_global,
                eth_payload=_eth_payload(),
                capture_timestamp_ms=CAPTURE_MS,
            )


if __name__ == "__main__":
    unittest.main()
