from __future__ import annotations

import unittest

from crypto_autopilot.derivatives_history import (
    DerivativesHistoryEvidenceError,
    FundingRateRecord,
    MarkPriceCandle,
    OpenInterestIndex,
    OpenInterestSnapshot,
    audit_funding_rate_records,
    audit_mark_price_candles,
    fetch_funding_rate_history,
    funding_points_from_records,
    mark_price_candles_available_as_of,
)
from crypto_autopilot.exchanges.pionex_public import PionexPublicClient


class _FundingClient:
    def __init__(self, pages: dict[int, list[FundingRateRecord]]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, int, int | None]] = []

    def get_funding_rates(
        self,
        symbol: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[FundingRateRecord]:
        self.calls.append((symbol, limit, end_time_ms))
        if end_time_ms is None:
            return []
        return list(self.pages.get(end_time_ms, []))


class _FakePionexPublicClient(PionexPublicClient):
    def __init__(self, responses: dict[str, dict]) -> None:
        super().__init__()
        self.responses = responses
        self.requests: list[tuple[str, dict[str, object]]] = []

    def _get_json(self, path: str, params: dict[str, object]) -> dict:
        self.requests.append((path, params))
        return self.responses[path]


class DerivativesHistoryTests(unittest.TestCase):
    def test_funding_history_pages_backward_without_assuming_cadence(self) -> None:
        symbol = "BTC_USDT_PERP"
        client = _FundingClient(
            {
                3000: [
                    FundingRateRecord(symbol, 3000, 0.0002, 9000),
                    FundingRateRecord(symbol, 2000, 0.0001, 9000),
                ],
                1999: [FundingRateRecord(symbol, 1000, -0.0001, 9001)],
            }
        )
        records = fetch_funding_rate_history(
            client,
            symbol=symbol,
            start_time_ms=1000,
            end_time_ms=3000,
        )
        self.assertEqual([item.funding_time_ms for item in records], [1000, 2000, 3000])
        self.assertEqual(client.calls, [(symbol, 500, 3000), (symbol, 500, 1999)])

    def test_conflicting_funding_timestamp_fails_closed(self) -> None:
        with self.assertRaises(DerivativesHistoryEvidenceError):
            audit_funding_rate_records(
                [
                    FundingRateRecord("BTC_USDT_PERP", 1000, 0.0001, 2000),
                    FundingRateRecord("BTC_USDT_PERP", 1000, 0.0002, 2001),
                ]
            )

    def test_funding_records_convert_to_backtest_points_without_retiming(self) -> None:
        records = [FundingRateRecord("BTC_USDT_PERP", 1234, 0.0003, 9999)]
        points = funding_points_from_records(records)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].symbol, "BTC_USDT_PERP")
        self.assertEqual(points[0].time_ms, 1234)
        self.assertEqual(points[0].rate, 0.0003)

    def test_mark_price_candle_is_not_available_before_close(self) -> None:
        candle = MarkPriceCandle(
            symbol="BTC_USDT_PERP",
            interval="15M",
            time_ms=0,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            retrieved_at_ms=10_000_000,
        )
        self.assertEqual(mark_price_candles_available_as_of([candle], as_of_ms=899_999), ())
        self.assertEqual(mark_price_candles_available_as_of([candle], as_of_ms=900_000), (candle,))

    def test_mark_price_gap_fails_closed(self) -> None:
        candles = [
            MarkPriceCandle("BTC_USDT_PERP", "15M", 0, 100, 101, 99, 100, 10_000),
            MarkPriceCandle("BTC_USDT_PERP", "15M", 1_800_000, 100, 101, 99, 100, 10_000),
        ]
        with self.assertRaises(DerivativesHistoryEvidenceError):
            audit_mark_price_candles(candles)

    def test_open_interest_never_backprojects_future_snapshot(self) -> None:
        index = OpenInterestIndex(
            [OpenInterestSnapshot("BTC_USDT_PERP", 123.0, observed_at_ms=2000)]
        )
        with self.assertRaises(DerivativesHistoryEvidenceError):
            index.latest_at_or_before(symbol="BTC_USDT_PERP", as_of_ms=1999, max_age_ms=1000)
        self.assertEqual(
            index.latest_at_or_before(symbol="BTC_USDT_PERP", as_of_ms=2500, max_age_ms=1000).open_interest,
            123.0,
        )
        with self.assertRaises(DerivativesHistoryEvidenceError):
            index.latest_at_or_before(symbol="BTC_USDT_PERP", as_of_ms=4001, max_age_ms=1000)

    def test_public_client_parses_funding_mark_and_open_interest(self) -> None:
        client = _FakePionexPublicClient(
            {
                "/api/v1/market/fundingRates": {
                    "result": True,
                    "timestamp": 9000,
                    "data": {
                        "symbol": "BTC_USDT_PERP",
                        "rates": [{"fundingRate": "0.0001", "fundingTime": 8000}],
                    },
                },
                "/api/v1/market/markKlines": {
                    "result": True,
                    "timestamp": 9000,
                    "data": {
                        "klines": [
                            {"time": "0", "open": "100", "close": "101", "high": "102", "low": "99"}
                        ]
                    },
                },
                "/api/v1/market/openInterests": {
                    "result": True,
                    "timestamp": 9000,
                    "data": {
                        "openInterests": [
                            {"symbol": "BTC_USDT_PERP", "openInterest": "123.45"}
                        ]
                    },
                },
            }
        )

        funding = client.get_funding_rates("BTC_USDT_PERP", end_time_ms=8500)
        mark = client.get_mark_price_klines("BTC_USDT_PERP", "15M", limit=1)
        oi = client.list_open_interests()

        self.assertEqual(funding[0].funding_time_ms, 8000)
        self.assertEqual(funding[0].retrieved_at_ms, 9000)
        self.assertEqual(mark[0].close, 101.0)
        self.assertEqual(mark[0].available_at_ms, 900_000)
        self.assertEqual(oi[0].open_interest, 123.45)
        self.assertEqual(oi[0].observed_at_ms, 9000)

        self.assertEqual(
            client.requests,
            [
                (
                    "/api/v1/market/fundingRates",
                    {"symbol": "BTC_USDT_PERP", "endTime": 8500, "limit": 500},
                ),
                (
                    "/api/v1/market/markKlines",
                    {"symbol": "BTC_USDT_PERP", "interval": "15M", "limit": 1},
                ),
                ("/api/v1/market/openInterests", {}),
            ],
        )

    def test_mark_price_client_does_not_expose_undocumented_end_time(self) -> None:
        client = _FakePionexPublicClient(
            {
                "/api/v1/market/markKlines": {
                    "result": True,
                    "timestamp": 1,
                    "data": {"klines": []},
                }
            }
        )
        client.get_mark_price_klines("BTC_USDT_PERP", "60M", limit=10)
        _, params = client.requests[0]
        self.assertNotIn("endTime", params)


if __name__ == "__main__":
    unittest.main()
