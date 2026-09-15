from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.backtest import FundingPoint
from crypto_autopilot.models import Candle
from crypto_autopilot.paper_long_short_challenger_v0_2 import (
    DirectionalPlan,
    run_long_short_exploration,
)


ROOT = Path(__file__).resolve().parents[1]


def _candles() -> tuple[Candle, ...]:
    return (
        Candle(1_000, 100.0, 101.0, 99.0, 100.0, 10.0),
        Candle(2_000, 100.0, 101.0, 98.5, 99.0, 10.0),
        Candle(3_000, 99.0, 99.5, 96.0, 97.0, 10.0),
        Candle(4_000, 97.0, 97.5, 96.5, 97.0, 10.0),
    )


class PaperLongShortChallengerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(
            (ROOT / "config" / "paper_long_short_challenger_v0_2.json").read_text(
                encoding="utf-8"
            )
        )

    def test_short_plan_has_inverse_geometry_and_can_profit(self) -> None:
        plan = DirectionalPlan(
            plan_id="short-target",
            symbol="BTC_USDT_PERP",
            side="SHORT",
            signal_time_ms=1_000,
            stop_price=102.0,
            target_price=97.5,
        )
        result = run_long_short_exploration(
            candles_by_symbol={plan.symbol: _candles()},
            plans=(plan,),
            config=self.config,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["accepted_sides"], ["SHORT"])
        self.assertEqual(result["by_side"]["short"]["trade_count"], 1)
        self.assertEqual(result["samples"][0]["exit_reason"], "target")
        self.assertGreater(result["samples"][0]["net_pnl_usd"], 0.0)

    def test_long_and_short_funding_are_accounted_with_opposite_signs(self) -> None:
        long_plan = DirectionalPlan(
            plan_id="long-end",
            symbol="BTC_USDT_PERP",
            side="LONG",
            signal_time_ms=1_000,
            stop_price=98.0,
            target_price=105.0,
        )
        short_plan = DirectionalPlan(
            plan_id="short-end",
            symbol="ETH_USDT_PERP",
            side="SHORT",
            signal_time_ms=1_000,
            stop_price=102.0,
            target_price=95.0,
        )
        funding = (
            FundingPoint("BTC_USDT_PERP", 2_000, 0.001),
            FundingPoint("ETH_USDT_PERP", 2_000, 0.001),
        )
        result = run_long_short_exploration(
            candles_by_symbol={
                "BTC_USDT_PERP": _candles(),
                "ETH_USDT_PERP": _candles(),
            },
            plans=(long_plan, short_plan),
            funding_points=funding,
            config=self.config,
        )
        self.assertEqual(result["by_side"]["long"]["trade_count"], 1)
        self.assertEqual(result["by_side"]["short"]["trade_count"], 1)
        self.assertGreater(result["samples"][0]["funding_usd"], 0.0)
        self.assertLess(result["samples"][1]["funding_usd"], 0.0)

    def test_limits_prevent_more_than_two_samples_per_symbol_day(self) -> None:
        plans = tuple(
            DirectionalPlan(
                plan_id=f"short-{index}",
                symbol="BTC_USDT_PERP",
                side="SHORT",
                signal_time_ms=1_000,
                stop_price=102.0,
                target_price=97.5,
            )
            for index in range(3)
        )
        result = run_long_short_exploration(
            candles_by_symbol={"BTC_USDT_PERP": _candles()},
            plans=plans,
            config=self.config,
        )
        self.assertEqual(result["by_side"]["short"]["trade_count"], 2)
        self.assertIn(
            ["short-2", "challenger_symbol_daily_sample_gate"],
            result["rejected_plans"],
        )

    def test_authority_is_research_only(self) -> None:
        plan = DirectionalPlan(
            plan_id="authority",
            symbol="BTC_USDT_PERP",
            side="SHORT",
            signal_time_ms=1_000,
            stop_price=102.0,
            target_price=97.5,
        )
        result = run_long_short_exploration(
            candles_by_symbol={plan.symbol: _candles()},
            plans=(plan,),
            config=self.config,
        )
        self.assertFalse(result["authority"]["r2_reads_authorized"])
        self.assertFalse(result["authority"]["r2_writes_authorized"])
        self.assertFalse(result["authority"]["automatic_model_promotion_authorized"])
        self.assertFalse(result["authority"]["live_trading_authorized"])
        self.assertTrue(result["interpretation"]["long_short_comparison_only"])

    def test_challenger_does_not_change_governed_long_only_baseline(self) -> None:
        baseline = json.loads(
            (ROOT / "config" / "strategy_v0_1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.config["status"], "PREPARED_LOCAL_REPLAY_ONLY")
        self.assertEqual(self.config["direction"], "LONG_SHORT")
        self.assertEqual(baseline["direction"], "LONG_ONLY")


if __name__ == "__main__":
    unittest.main()
