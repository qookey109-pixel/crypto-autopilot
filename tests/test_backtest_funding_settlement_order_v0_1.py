from __future__ import annotations

import unittest

from crypto_autopilot.backtest import (
    BacktestConfig,
    FundingPoint,
    LongTradePlan,
    run_long_backtest,
)
from crypto_autopilot.models import Candle

MINUTE = 60_000
SYMBOL = "BTC_USDT_PERP"


def candle(index: int, *, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(
        time_ms=index * MINUTE,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
    )


class FundingSettlementOrderV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.candles = [
            candle(0, open_=99.0, high=101.0, low=98.0, close=100.0),
            candle(1, open_=100.0, high=103.0, low=99.0, close=102.0),
            candle(2, open_=102.0, high=111.0, low=101.0, close=110.0),
        ]
        self.plan = LongTradePlan("funding-order", SYMBOL, 0, 95.0, 110.0)
        self.config = BacktestConfig(taker_fee_bps=0, slippage_bps=0)

    def run_with(self, *points: FundingPoint):
        return run_long_backtest(
            candles_by_symbol={SYMBOL: self.candles},
            plans=[self.plan],
            funding_points=list(points),
            config=self.config,
        ).trades[0]

    def test_entry_timestamp_funding_is_already_settled_before_new_fill(self) -> None:
        trade = self.run_with(FundingPoint(SYMBOL, MINUTE, 0.01))
        self.assertEqual(trade.entry_time_ms, MINUTE)
        self.assertEqual(trade.funding_usd, 0.0)

    def test_funding_after_entry_and_at_exit_are_charged(self) -> None:
        during = self.run_with(FundingPoint(SYMBOL, 90_000, 0.01))
        at_exit = self.run_with(FundingPoint(SYMBOL, 2 * MINUTE, 0.01))
        combined = self.run_with(
            FundingPoint(SYMBOL, MINUTE, 0.01),
            FundingPoint(SYMBOL, 90_000, 0.01),
            FundingPoint(SYMBOL, 2 * MINUTE, 0.01),
        )
        self.assertGreater(during.funding_usd, 0.0)
        self.assertGreater(at_exit.funding_usd, 0.0)
        self.assertAlmostEqual(
            combined.funding_usd,
            during.funding_usd + at_exit.funding_usd,
            places=7,
        )


if __name__ == "__main__":
    unittest.main()
