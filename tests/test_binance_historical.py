from __future__ import annotations

import unittest
from unittest.mock import patch

from crypto_autopilot.binance_historical import (
    BINANCE_INTERVAL_MS,
    OPEN_INTEREST_PROJECT_WINDOW_MS,
    BinanceHistoricalEvidenceError,
    backfill_binance_funding_rates,
    backfill_binance_klines,
    backfill_binance_mark_price,
    backfill_binance_open_interest,
    binance_usdm_to_pionex_perp,
    pionex_perp_to_binance_usdm,
    to_backtest_funding_points,
)
from crypto_autopilot.exchanges.binance_usdm_public import (
    BinanceFundingRate,
    BinanceMarkPriceCandle,
    BinanceOpenInterestPoint,
    BinanceUSDMPublicClient,
)
from crypto_autopilot.models import Candle


class FakeBinanceHistoricalClient:
    def __init__(self) -> None:
        self.kline_calls: list[tuple[int | None, int | None, int]] = []
        self.mark_calls: list[tuple[int | None, int | None, int]] = []
        self.funding_calls: list[tuple[int | None, int | None, int]] = []
        self.oi_calls: list[tuple[int | None, int | None, int]] = []
        self.klines: tuple[Candle, ...] = ()
        self.mark: tuple[BinanceMarkPriceCandle, ...] = ()
        self.funding: tuple[BinanceFundingRate, ...] = ()
        self.oi: tuple[BinanceOpenInterestPoint, ...] = ()

    @staticmethod
    def _page(items, *, key, start_time_ms, end_time_ms, limit):
        return [
            item
            for item in items
            if (start_time_ms is None or key(item) >= start_time_ms)
            and (end_time_ms is None or key(item) <= end_time_ms)
        ][:limit]

    def get_klines(self, symbol, interval, *, start_time_ms=None, end_time_ms=None, limit=1500):
        self.kline_calls.append((start_time_ms, end_time_ms, limit))
        return self._page(
            self.klines,
            key=lambda item: item.time_ms,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            limit=limit,
        )

    def get_mark_price_klines(self, symbol, interval, *, start_time_ms=None, end_time_ms=None, limit=1500):
        self.mark_calls.append((start_time_ms, end_time_ms, limit))
        return self._page(
            self.mark,
            key=lambda item: item.open_time_ms,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            limit=limit,
        )

    def get_funding_rates(self, symbol, *, start_time_ms=None, end_time_ms=None, limit=1000):
        self.funding_calls.append((start_time_ms, end_time_ms, limit))
        return self._page(
            self.funding,
            key=lambda item: item.funding_time_ms,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            limit=limit,
        )

    def get_open_interest_history(self, symbol, period, *, start_time_ms=None, end_time_ms=None, limit=500):
        self.oi_calls.append((start_time_ms, end_time_ms, limit))
        return self._page(
            self.oi,
            key=lambda item: item.timestamp_ms,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            limit=limit,
        )


class BinanceHistoricalSourceTests(unittest.TestCase):
    def test_symbol_mapping_is_syntactic_not_provenance_conversion(self) -> None:
        self.assertEqual(pionex_perp_to_binance_usdm("BTC_USDT_PERP"), "BTCUSDT")
        self.assertEqual(binance_usdm_to_pionex_perp("BTCUSDT"), "BTC_USDT_PERP")
        with self.assertRaises(ValueError):
            pionex_perp_to_binance_usdm("BTC_USDC_PERP")

    def test_kline_backfill_paginates_forward_and_audits(self) -> None:
        client = FakeBinanceHistoricalClient()
        step = BINANCE_INTERVAL_MS["15m"]
        client.klines = tuple(
            Candle(time_ms=index * step, open=100 + index, high=102 + index, low=99 + index, close=101 + index, volume=10)
            for index in range(3)
        )
        result = backfill_binance_klines(
            client,
            "BTCUSDT",
            "15m",
            start_time_ms=0,
            end_time_ms=2 * step,
            page_limit=2,
        )
        self.assertEqual(result.pages_fetched, 2)
        self.assertEqual([item.time_ms for item in result.candles], [0, step, 2 * step])
        self.assertTrue(result.audit.ok)
        self.assertFalse(result.provenance.native_to_execution_exchange)
        self.assertFalse(result.provenance.may_authorize_pionex_native_history)
        self.assertTrue(result.provenance.requires_equivalence_gate)
        self.assertEqual(client.kline_calls[1][0], 2 * step)

    def test_mark_price_history_requires_contiguous_closed_bars(self) -> None:
        client = FakeBinanceHistoricalClient()
        step = BINANCE_INTERVAL_MS["1h"]
        client.mark = tuple(
            BinanceMarkPriceCandle(
                symbol="BTCUSDT",
                interval="1h",
                open_time_ms=index * step,
                close_time_ms=(index + 1) * step - 1,
                open=100 + index,
                high=102 + index,
                low=99 + index,
                close=101 + index,
            )
            for index in range(3)
        )
        result = backfill_binance_mark_price(
            client,
            "BTCUSDT",
            "1h",
            start_time_ms=0,
            end_time_ms=2 * step,
            page_limit=2,
        )
        self.assertEqual(result.pages_fetched, 2)
        self.assertEqual(result.candles[0].available_at_ms, step)
        self.assertEqual(result.candles[-1].available_at_ms, 3 * step)

        client.mark = (client.mark[0], client.mark[2])
        with self.assertRaises(BinanceHistoricalEvidenceError):
            backfill_binance_mark_price(
                client,
                "BTCUSDT",
                "1h",
                start_time_ms=0,
                end_time_ms=2 * step,
            )

    def test_funding_history_paginates_and_maps_to_backtest_without_relabelling_provider(self) -> None:
        client = FakeBinanceHistoricalClient()
        client.funding = (
            BinanceFundingRate("BTCUSDT", 1000, 0.0001, 100.0, "Regular"),
            BinanceFundingRate("BTCUSDT", 2000, -0.0002, 101.0, "Regular"),
            BinanceFundingRate("BTCUSDT", 3000, 0.0003, 102.0, "Regular"),
        )
        result = backfill_binance_funding_rates(
            client,
            "BTCUSDT",
            start_time_ms=1000,
            end_time_ms=3000,
            page_limit=2,
        )
        self.assertEqual(result.pages_fetched, 2)
        self.assertEqual([point.funding_time_ms for point in result.points], [1000, 2000, 3000])
        self.assertEqual(client.funding_calls[1][0], 2001)
        converted = to_backtest_funding_points(result)
        self.assertEqual([point.symbol for point in converted], ["BTC_USDT_PERP"] * 3)
        self.assertEqual([point.rate for point in converted], [0.0001, -0.0002, 0.0003])
        self.assertEqual(result.provenance.provider, "binance_usdm")

    def test_open_interest_is_fail_closed_outside_conservative_30_day_window(self) -> None:
        client = FakeBinanceHistoricalClient()
        now_ms = 100 * 24 * 60 * 60 * 1000
        with self.assertRaises(BinanceHistoricalEvidenceError):
            backfill_binance_open_interest(
                client,
                "BTCUSDT",
                "1h",
                start_time_ms=now_ms - OPEN_INTEREST_PROJECT_WINDOW_MS - 1,
                end_time_ms=now_ms,
                now_ms=now_ms,
            )

        start = now_ms - 2 * 60 * 60 * 1000
        client.oi = (
            BinanceOpenInterestPoint("BTCUSDT", "1h", start, 10.0, 1000.0),
            BinanceOpenInterestPoint("BTCUSDT", "1h", start + 60 * 60 * 1000, 11.0, 1100.0),
        )
        result = backfill_binance_open_interest(
            client,
            "BTCUSDT",
            "1h",
            start_time_ms=start,
            end_time_ms=now_ms,
            now_ms=now_ms,
        )
        self.assertEqual(len(result.points), 2)
        self.assertEqual(result.provenance.provider, "binance_usdm")

    def test_public_client_uses_documented_endpoints_and_parses_payloads(self) -> None:
        client = BinanceUSDMPublicClient()
        with patch.object(
            client,
            "_get_json",
            return_value=[[0, "1", "2", "0.5", "1.5", "10", 899999, "0", 1, "0", "0", "0"]],
        ) as request:
            rows = client.get_mark_price_klines("BTCUSDT", "15m", start_time_ms=0, end_time_ms=899999)
            self.assertEqual(rows[0].close, 1.5)
            self.assertEqual(request.call_args.args[0], "/fapi/v1/markPriceKlines")
            self.assertEqual(request.call_args.args[1]["startTime"], 0)
            self.assertEqual(request.call_args.args[1]["endTime"], 899999)

        with patch.object(
            client,
            "_get_json",
            return_value=[
                {
                    "symbol": "BTCUSDT",
                    "fundingTime": 1000,
                    "fundingRate": "0.0001",
                    "markPrice": "100.5",
                    "rateType": "Regular",
                }
            ],
        ) as request:
            rows = client.get_funding_rates("BTCUSDT", start_time_ms=1000, end_time_ms=2000)
            self.assertEqual(rows[0].rate, 0.0001)
            self.assertEqual(request.call_args.args[0], "/fapi/v1/fundingRate")

        with patch.object(
            client,
            "_get_json",
            return_value=[
                {
                    "symbol": "BTCUSDT",
                    "sumOpenInterest": "10",
                    "sumOpenInterestValue": "1000",
                    "timestamp": 1000,
                }
            ],
        ) as request:
            rows = client.get_open_interest_history("BTCUSDT", "1h", start_time_ms=1000, end_time_ms=2000)
            self.assertEqual(rows[0].sum_open_interest_value, 1000.0)
            self.assertEqual(request.call_args.args[0], "/futures/data/openInterestHist")


if __name__ == "__main__":
    unittest.main()
