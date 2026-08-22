from __future__ import annotations

import unittest

from crypto_autopilot.advanced_technical import build_advanced_technical_series
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.market_features import (
    DerivativeIndexSnapshot,
    FundingRateObservation,
    OrderBookSnapshot,
    PublicTrade,
    build_derivative_features,
    build_microstructure_features,
)
from crypto_autopilot.models import Candle


def _candles(count: int) -> list[Candle]:
    step = INTERVAL_MS["15M"]
    closes = [100.0 + index * 0.08 + (index % 9) * 0.03 for index in range(count)]
    return [
        Candle(
            time_ms=index * step,
            open=close - 0.05,
            high=close + 0.7,
            low=close - 0.7,
            close=close,
            volume=100.0 + index % 13,
        )
        for index, close in enumerate(closes)
    ]


class AdvancedTechnicalTests(unittest.TestCase):
    def test_advanced_features_warm_up_and_are_causal(self) -> None:
        source = _candles(240)
        baseline = build_advanced_technical_series(source, "15M")
        self.assertTrue(baseline[-1].ready)
        self.assertGreater(baseline[-1].adx14 or 0.0, 0.0)
        self.assertGreater(baseline[-1].rolling_vwap20 or 0.0, 0.0)
        self.assertEqual(
            baseline[-1].available_at_ms,
            source[-1].time_ms + INTERVAL_MS["15M"],
        )

        mutated = list(source)
        for index in range(180, len(mutated)):
            item = mutated[index]
            mutated[index] = Candle(
                item.time_ms,
                item.open * 2,
                item.high * 2,
                item.low * 2,
                item.close * 2,
                item.volume * 3,
            )
        changed = build_advanced_technical_series(mutated, "15M")
        self.assertEqual(baseline[:180], changed[:180])

    def test_donchian_range_excludes_current_bar(self) -> None:
        source = _candles(25)
        breakout = source[20]
        source[20] = Candle(
            breakout.time_ms,
            breakout.open,
            breakout.close + 20.0,
            breakout.low,
            breakout.close + 10.0,
            breakout.volume,
        )
        snapshot = build_advanced_technical_series(source, "15M")[20]
        self.assertGreater(snapshot.donchian_position20 or 0.0, 1.0)


class MarketFeatureTests(unittest.TestCase):
    def test_microstructure_features_are_notional_weighted(self) -> None:
        trades = (
            PublicTrade("BTC_USDT_PERP", "1", 100.0, 3.0, "BUY", 1),
            PublicTrade("BTC_USDT_PERP", "2", 100.0, 1.0, "SELL", 2),
        )
        book = OrderBookSnapshot(
            "BTC_USDT_PERP",
            bids=((99.0, 2.0),),
            asks=((101.0, 3.0), (102.0, 10.0)),
            update_time_ms=3,
        )
        features = build_microstructure_features(
            trades, book, depth_levels=2, reference_notional_usd=500.0
        )
        self.assertAlmostEqual(features.trade_imbalance or 0.0, 0.5)
        self.assertEqual(features.cumulative_volume_delta, 2.0)
        self.assertGreater(features.spread_bps or 0.0, 0.0)
        self.assertGreater(features.expected_buy_slippage_bps or 0.0, 0.0)

    def test_derivative_features_include_percentile_basis_and_oi_change(self) -> None:
        current = DerivativeIndexSnapshot(
            "BTC_USDT_PERP", 100.0, 101.0, 0.002, 10, 9
        )
        history = tuple(
            FundingRateObservation("BTC_USDT_PERP", index, rate)
            for index, rate in enumerate((-0.001, 0.0, 0.001, 0.003))
        )
        features = build_derivative_features(
            current=current,
            funding_history=history,
            basis_history=(-0.01, 0.0, 0.005),
            open_interest=120.0,
            previous_open_interest=100.0,
        )
        self.assertEqual(features.funding_percentile, 0.75)
        self.assertAlmostEqual(features.mark_index_basis or 0.0, 0.01)
        self.assertIsNotNone(features.basis_zscore)
        self.assertAlmostEqual(features.open_interest_change_fraction or 0.0, 0.2)


if __name__ == "__main__":
    unittest.main()
