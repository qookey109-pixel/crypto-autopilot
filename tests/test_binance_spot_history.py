from __future__ import annotations

import json
import unittest
from urllib.parse import parse_qs, urlparse

from crypto_autopilot.binance_spot_history import (
    BinanceSpotHistoryError,
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
    def test_parse_spot_kline_preserves_provider_fields(self) -> None:
        candle = parse_spot_kline("BTCUSDT", row(1_577_836_800_000))
        self.assertEqual(candle.symbol, "BTCUSDT")
        self.assertEqual(candle.close, 101.0)
        self.assertEqual(candle.quote_volume, 1262.5)
        self.assertEqual(candle.trade_count, 42)

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


if __name__ == "__main__":
    unittest.main()
