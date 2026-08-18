from __future__ import annotations

import unittest

from crypto_autopilot.backtest import (
    BacktestConfig,
    FundingPoint,
    LongTradePlan,
    run_long_backtest,
)
from crypto_autopilot.models import Candle
from crypto_autopilot.risk import RiskConfig


MINUTE = 60_000


def candle(index: int, *, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(
        time_ms=index * MINUTE,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
    )


class BacktestEngineTest(unittest.TestCase):
    def test_signal_cannot_fill_until_next_bar(self) -> None:
        candles = [
            candle(0, open_=99, high=101, low=98, close=100),
            candle(1, open_=100, high=103, low=99, close=102),
            candle(2, open_=102, high=111, low=101, close=110),
        ]
        result = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=[LongTradePlan("p1", "BTC_USDT_PERP", 0, 95.0, 110.0)],
            config=BacktestConfig(taker_fee_bps=0, slippage_bps=0),
        )
        self.assertEqual(len(result.trades), 1)
        trade = result.trades[0]
        self.assertEqual(trade.entry_time_ms, MINUTE)
        self.assertGreater(trade.entry_time_ms, trade.signal_time_ms)
        self.assertEqual(trade.exit_time_ms, 2 * MINUTE)
        self.assertEqual(trade.exit_reason, "target")
        self.assertEqual(trade.raw_entry_price, 100.0)
        self.assertEqual(trade.raw_exit_price, 110.0)

    def test_same_bar_stop_target_collision_is_conservatively_stop_first(self) -> None:
        candles = [
            candle(0, open_=100, high=101, low=99, close=100),
            candle(1, open_=100, high=112, low=94, close=105),
        ]
        result = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=[LongTradePlan("collision", "BTC_USDT_PERP", 0, 95.0, 110.0)],
            config=BacktestConfig(taker_fee_bps=0, slippage_bps=0),
        )
        self.assertEqual(result.trades[0].exit_reason, "stop_same_bar_collision")
        self.assertEqual(result.trades[0].raw_exit_price, 95.0)
        self.assertLess(result.trades[0].net_pnl_usd, 0)

    def test_last_bar_signal_is_rejected_instead_of_lookahead_fill(self) -> None:
        candles = [candle(0, open_=100, high=102, low=99, close=101)]
        result = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=[LongTradePlan("last", "BTC_USDT_PERP", 0, 95.0, 110.0)],
        )
        self.assertEqual(result.trades, ())
        self.assertEqual(result.rejected_plans, (("last", "no_future_entry_bar"),))

    def test_fee_slippage_and_funding_are_explicit_and_deterministic(self) -> None:
        candles = [
            candle(0, open_=100, high=101, low=99, close=100),
            candle(1, open_=100, high=103, low=99, close=102),
            candle(2, open_=102, high=111, low=101, close=110),
        ]
        plan = LongTradePlan("costs", "BTC_USDT_PERP", 0, 95.0, 110.0)
        funding = [FundingPoint("BTC_USDT_PERP", 90_000, 0.0001)]
        config = BacktestConfig(taker_fee_bps=5, slippage_bps=2)
        first = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=[plan],
            funding_points=funding,
            config=config,
        )
        second = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=[plan],
            funding_points=funding,
            config=config,
        )
        self.assertEqual(first, second)
        trade = first.trades[0]
        self.assertGreater(trade.fees_usd, 0)
        self.assertGreater(trade.funding_usd, 0)
        self.assertGreater(trade.slippage_cost_usd, 0)
        self.assertLess(trade.net_pnl_usd, trade.gross_pnl_usd)
        self.assertAlmostEqual(first.metrics.net_pnl_usd, trade.net_pnl_usd, places=7)

    def test_existing_daily_trade_count_gate_is_honored(self) -> None:
        candles = [
            candle(0, open_=100, high=101, low=99, close=100),
            candle(1, open_=100, high=106, low=99, close=105),
            candle(2, open_=105, high=111, low=104, close=110),
            candle(3, open_=100, high=101, low=99, close=100),
            candle(4, open_=100, high=111, low=99, close=110),
        ]
        plans = [
            LongTradePlan("one", "BTC_USDT_PERP", 0, 95.0, 110.0),
            LongTradePlan("two", "BTC_USDT_PERP", 2 * MINUTE, 95.0, 110.0),
        ]
        config = BacktestConfig(
            taker_fee_bps=0,
            slippage_bps=0,
            risk=RiskConfig(max_new_trades_per_day=1),
        )
        result = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=plans,
            config=config,
        )
        self.assertEqual(len(result.trades), 1)
        self.assertIn(("two", "daily_trade_count_gate"), result.rejected_plans)

    def test_overlapping_signal_is_rejected_while_position_is_open(self) -> None:
        candles = [
            candle(0, open_=100, high=101, low=99, close=100),
            candle(1, open_=100, high=102, low=99, close=101),
            candle(2, open_=101, high=102, low=100, close=101),
            candle(3, open_=101, high=111, low=100, close=110),
        ]
        result = run_long_backtest(
            candles_by_symbol={"BTC_USDT_PERP": candles},
            plans=[
                LongTradePlan("primary", "BTC_USDT_PERP", 0, 95.0, 110.0),
                LongTradePlan("overlap", "BTC_USDT_PERP", MINUTE, 95.0, 110.0),
            ],
            config=BacktestConfig(taker_fee_bps=0, slippage_bps=0),
        )
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].plan_id, "primary")
        self.assertIn(("overlap", "position_overlap"), result.rejected_plans)


if __name__ == "__main__":
    unittest.main()
