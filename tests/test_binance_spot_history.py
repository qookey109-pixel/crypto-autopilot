from __future__ import annotations

import json
import unittest
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from crypto_autopilot.binance_spot_history import (
    BINANCE_SPOT_KLINES_URL,
    BinanceSpotHistoryError,
    ProviderReadDeadlineExceeded,
    fetch_spot_history,
    parse_spot_kline,
)


DAY_MS = 86_400_000


def row(timestamp: int, close: str = "101") -> list[object]:
    return [
        timestamp,
        "100",
        "103",
        "99",
        close,
        "12.5",
        timestamp + DAY_MS - 1,
        "1262.5",
        42,
        "6.0",
        "606.0",
        "0",
    ]


class BinanceSpotHistoryTests(unittest.TestCase):
    def test_uses_official_market_data_only_endpoint(self) -> None:
        self.assertEqual(
            BINANCE_SPOT_KLINES_URL,
            "https://data-api.binance.vision/api/v3/klines",
        )

    def test_parse_spot_kline_preserves_provider_fields(self) -> None:
        candle = parse_spot_kline("BTCUSDT", row(1_577_836_800_000))
        self.assertEqual(candle.symbol, "BTCUSDT")
        self.assertEqual(candle.close, 101.0)
        self.assertEqual(candle.quote_volume, 1262.5)
        self.assertEqual(candle.trade_count, 42)
        self.assertEqual(candle.taker_buy_base_volume, 6.0)
        self.assertEqual(candle.taker_buy_quote_volume, 606.0)

    def test_taker_buy_volume_cannot_exceed_total_volume(self) -> None:
        invalid = row(1_577_836_800_000)
        invalid[10] = "2000"
        with self.assertRaisesRegex(BinanceSpotHistoryError, "taker-buy"):
            parse_spot_kline("BTCUSDT", invalid)

    def test_forward_pagination_deduplicates_and_audits(self) -> None:
        start = 1_577_836_800_000
        calls: list[int] = []

        def transport(url: str, _timeout: float) -> bytes:
            cursor = int(parse_qs(urlparse(url).query)["startTime"][0])
            calls.append(cursor)
            if len(calls) == 1:
                payload = [row(start), row(start + DAY_MS)]
            else:
                payload = [row(start + 2 * DAY_MS, "102")]
            return json.dumps(payload).encode()

        result = fetch_spot_history(
            "BTCUSDT",
            start_time_ms=start,
            end_time_ms=start + 2 * DAY_MS,
            page_limit=2,
            requests_per_second=1000,
            transport=transport,
            sleep_fn=lambda _seconds: None,
        )
        self.assertEqual(calls, [start, start + 2 * DAY_MS])
        self.assertEqual(len(result.candles), 3)
        self.assertTrue(result.audit_ok)
        self.assertEqual(
            result.audit_evidence,
            {
                "expected_last_open_time_ms": start + 2 * DAY_MS,
                "actual_first_open_time_ms": start,
                "actual_last_open_time_ms": start + 2 * DAY_MS,
                "tail_missing_bars": 0,
                "tail_complete": True,
            },
        )

    def test_contiguous_but_stale_tail_fails_audit_with_coverage_evidence(self) -> None:
        start = 1_577_836_800_000
        result = fetch_spot_history(
            "BTCUSDT",
            start_time_ms=start,
            end_time_ms=start + 2 * DAY_MS,
            requests_per_second=1000,
            transport=lambda _url, _timeout: json.dumps(
                [row(start), row(start + DAY_MS)]
            ).encode(),
            sleep_fn=lambda _seconds: None,
        )

        self.assertFalse(result.audit_ok)
        self.assertEqual(
            result.audit_evidence,
            {
                "expected_last_open_time_ms": start + 2 * DAY_MS,
                "actual_first_open_time_ms": start,
                "actual_last_open_time_ms": start + DAY_MS,
                "tail_missing_bars": 1,
                "tail_complete": False,
            },
        )

    def test_late_listing_can_pass_when_requested_tail_is_complete(self) -> None:
        start = 1_577_836_800_000
        result = fetch_spot_history(
            "BTCUSDT",
            start_time_ms=start,
            end_time_ms=start + 2 * DAY_MS,
            requests_per_second=1000,
            transport=lambda _url, _timeout: json.dumps(
                [row(start + DAY_MS), row(start + 2 * DAY_MS)]
            ).encode(),
            sleep_fn=lambda _seconds: None,
        )

        self.assertTrue(result.audit_ok)
        self.assertEqual(result.actual_first_open_time_ms, start + DAY_MS)
        self.assertEqual(result.tail_missing_bars, 0)

    def test_rejects_invalid_ohlc(self) -> None:
        invalid = row(1_577_836_800_000)
        invalid[2] = "90"
        with self.assertRaises(BinanceSpotHistoryError):
            parse_spot_kline("BTCUSDT", invalid)

    def test_rejects_lowercase_symbol(self) -> None:
        with self.assertRaises(ValueError):
            fetch_spot_history(
                "btcusdt",
                start_time_ms=0,
                end_time_ms=DAY_MS,
                transport=lambda _url, _timeout: b"[]",
            )

    def test_deadline_blocks_first_request_at_exact_stop(self) -> None:
        calls: list[str] = []

        def transport(url: str, _timeout: float) -> bytes:
            calls.append(url)
            return b"[]"

        with self.assertRaises(ProviderReadDeadlineExceeded):
            fetch_spot_history(
                "BTCUSDT",
                start_time_ms=0,
                end_time_ms=DAY_MS,
                provider_read_stop_ms=2_000_000,
                clock_fn=lambda: 2_000.0,
                transport=transport,
                sleep_fn=lambda _seconds: None,
            )

        self.assertEqual(calls, [])

    def test_deadline_is_rechecked_before_each_page(self) -> None:
        start = 1_577_836_800_000
        observed_times = iter((1_999.0, 2_000.0))
        calls: list[str] = []

        def transport(url: str, _timeout: float) -> bytes:
            calls.append(url)
            return json.dumps([row(start)]).encode()

        with self.assertRaises(ProviderReadDeadlineExceeded):
            fetch_spot_history(
                "BTCUSDT",
                start_time_ms=start,
                end_time_ms=start + DAY_MS,
                page_limit=1,
                requests_per_second=1_000,
                provider_read_stop_ms=2_000_000,
                clock_fn=lambda: next(observed_times),
                transport=transport,
                sleep_fn=lambda _seconds: None,
            )

        self.assertEqual(len(calls), 1)

    def test_deadline_is_rechecked_before_each_retry(self) -> None:
        observed_times = iter((1_999.0, 2_000.0))
        calls: list[str] = []

        def transport(url: str, _timeout: float) -> bytes:
            calls.append(url)
            raise URLError("temporary fixture failure")

        with self.assertRaises(ProviderReadDeadlineExceeded):
            fetch_spot_history(
                "BTCUSDT",
                start_time_ms=0,
                end_time_ms=DAY_MS,
                max_retries=1,
                requests_per_second=1_000,
                provider_read_stop_ms=2_000_000,
                clock_fn=lambda: next(observed_times),
                transport=transport,
                sleep_fn=lambda _seconds: None,
                random_fn=lambda: 0.0,
            )

        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
