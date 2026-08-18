import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from crypto_autopilot.historical import (
    PacedKlineClient,
    audit_candles,
    backfill_klines,
    write_backfill_json,
)
from crypto_autopilot.models import Candle

STEP = 15 * 60 * 1000


def candle(index: int, *, high: float = 102.0, low: float = 98.0) -> Candle:
    return Candle(
        time_ms=index * STEP,
        open=100.0,
        high=high,
        low=low,
        close=101.0,
        volume=10.0,
    )


class FakeClient:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.end_times: list[int | None] = []

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        self.end_times.append(end_time_ms)
        eligible = [item for item in self.candles if end_time_ms is None or item.time_ms <= end_time_ms]
        return eligible[-limit:]


class RateLimitThenSuccessClient:
    def __init__(self) -> None:
        self.calls = 0

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        del symbol, interval, limit, end_time_ms
        self.calls += 1
        if self.calls == 1:
            raise HTTPError("https://api.pionex.com", 429, "rate limited", None, None)
        return [candle(1)]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class HistoricalTests(unittest.TestCase):
    def test_audit_accepts_clean_contiguous_candles(self) -> None:
        audit = audit_candles([candle(1), candle(2), candle(3)], "15M")
        self.assertTrue(audit.ok)
        self.assertEqual(audit.count, 3)

    def test_audit_detects_duplicates_gaps_and_invalid_ohlc(self) -> None:
        rows = [candle(1), candle(2), candle(2), candle(4, high=99.0)]
        audit = audit_candles(rows, "15M")
        self.assertFalse(audit.ok)
        self.assertEqual(audit.duplicate_timestamps, (2 * STEP,))
        self.assertEqual(audit.gaps[0].missing_bars, 1)
        self.assertEqual(audit.invalid_candle_timestamps, (4 * STEP,))

    def test_backfill_pages_backwards_without_boundary_duplicates(self) -> None:
        client = FakeClient([candle(index) for index in range(10)])
        result = backfill_klines(
            client,
            "BTC_USDT_PERP",
            "15M",
            start_time_ms=2 * STEP,
            end_time_ms=8 * STEP,
            page_limit=3,
        )
        self.assertEqual([item.time_ms for item in result.candles], [i * STEP for i in range(2, 9)])
        self.assertEqual(client.end_times, [8 * STEP, 6 * STEP - 1, 3 * STEP - 1])
        self.assertEqual(result.pages_fetched, 3)
        self.assertTrue(result.audit.ok)

    def test_fixture_writer_is_deterministic(self) -> None:
        result = backfill_klines(
            FakeClient([candle(index) for index in range(5)]),
            "BTC_USDT_PERP",
            "15M",
            start_time_ms=STEP,
            end_time_ms=4 * STEP,
            page_limit=5,
        )
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.json"
            second = Path(directory) / "b.json"
            write_backfill_json(first, result)
            write_backfill_json(second, result)
            self.assertEqual(first.read_text(), second.read_text())
            payload = json.loads(first.read_text())
            self.assertEqual(payload["source"], "pionex_futures_klines")
            self.assertTrue(payload["audit"]["ok"])

    def test_paced_client_backs_off_after_http_429(self) -> None:
        delegate = RateLimitThenSuccessClient()
        clock = FakeClock()
        client = PacedKlineClient(
            delegate,
            requests_per_second=3.0,
            retry_after_seconds=65.0,
            max_429_retries=2,
            jitter_seconds=0.0,
            sleep_fn=clock.sleep,
            monotonic_fn=clock.monotonic,
            random_fn=lambda: 0.0,
        )
        rows = client.get_klines("BTC_USDT_PERP", "15M")
        self.assertEqual(rows, [candle(1)])
        self.assertEqual(delegate.calls, 2)
        self.assertEqual(clock.sleeps, [65.0])

    def test_paced_client_enforces_soft_request_interval(self) -> None:
        delegate = FakeClient([candle(1)])
        clock = FakeClock()
        client = PacedKlineClient(
            delegate,
            requests_per_second=2.0,
            jitter_seconds=0.0,
            sleep_fn=clock.sleep,
            monotonic_fn=clock.monotonic,
            random_fn=lambda: 0.0,
        )
        client.get_klines("BTC_USDT_PERP", "15M")
        client.get_klines("BTC_USDT_PERP", "15M")
        self.assertEqual(clock.sleeps, [0.5])


if __name__ == "__main__":
    unittest.main()
