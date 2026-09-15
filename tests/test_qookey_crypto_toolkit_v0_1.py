from __future__ import annotations

import unittest

from crypto_autopilot.toolkit import (
    evaluate_strategy,
    get_indicators,
    list_capabilities,
    run_paper_backtest,
    size_long_trade_tool,
)


class QookeyCryptoToolkitV01Tests(unittest.TestCase):
    def test_capabilities_are_research_only_and_fail_closed(self) -> None:
        result = list_capabilities()
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertEqual(
            {tool["name"] for tool in result["tools"]},
            {
                "get_indicators",
                "evaluate_strategy",
                "size_long_trade",
                "run_paper_backtest",
            },
        )
        self.assertTrue(all(value is False for value in result["safety_boundary"].values()))
        self.assertTrue(all(tool["side_effects"] == "none" for tool in result["tools"]))

    def test_indicator_facade_uses_existing_v0_2_indicator_set(self) -> None:
        candles = []
        for index in range(240):
            close = 100.0 + index * 0.1
            candles.append(
                {
                    "time_ms": index * 3_600_000,
                    "open": close - 0.2,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1_000.0 + index,
                }
            )
        result = get_indicators(candles, interval="1h")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["candle_count"], 240)
        self.assertTrue(result["latest_ready_v0_2"])
        latest = result["latest"]
        self.assertIsNotNone(latest["ema200"])
        self.assertIsNotNone(latest["rsi14"])
        self.assertIsNotNone(latest["macd_histogram"])
        self.assertIsNotNone(latest["bollinger_position"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_strategy_and_risk_facades_preserve_core_decisions(self) -> None:
        strategy = evaluate_strategy(
            {
                "symbol": "BTCUSDT",
                "sstate": {
                    "state": "S3",
                    "probability": 0.80,
                    "samples": 100,
                    "available": True,
                },
                "setup": {
                    "ema20_above_ema50": True,
                    "ema20_slope_positive": True,
                    "close_above_ema20": True,
                    "not_overextended": True,
                },
                "entry": {
                    "pullback_seen": True,
                    "reclaimed_ema20": True,
                    "broke_previous_high": True,
                    "volume_confirmed": True,
                },
                "reward_risk": 2.5,
                "liquidity_ok": True,
                "funding_ok": True,
            }
        )
        self.assertTrue(strategy["decision"]["eligible"])
        self.assertEqual(strategy["decision"]["reason"], "eligible")

        risk = size_long_trade_tool(
            {
                "equity_usd": 10_000.0,
                "entry_price": 100.0,
                "stop_price": 95.0,
            }
        )
        self.assertTrue(risk["decision"]["approved"])
        self.assertEqual(risk["decision"]["reason"], "approved")
        self.assertTrue(all(value is False for value in risk["authority"].values()))

    def test_backtest_facade_is_explicitly_paper_only(self) -> None:
        result = run_paper_backtest(
            {
                "candles_by_symbol": {
                    "BTCUSDT": [
                        {
                            "time_ms": 0,
                            "open": 100.0,
                            "high": 101.0,
                            "low": 99.0,
                            "close": 100.0,
                            "volume": 10.0,
                        },
                        {
                            "time_ms": 60_000,
                            "open": 100.0,
                            "high": 106.0,
                            "low": 99.0,
                            "close": 105.0,
                            "volume": 12.0,
                        },
                    ]
                },
                "plans": [
                    {
                        "plan_id": "paper-1",
                        "symbol": "BTCUSDT",
                        "signal_time_ms": 0,
                        "stop_price": 95.0,
                        "target_price": 105.0,
                    }
                ],
                "config": {
                    "taker_fee_bps": 0.0,
                    "slippage_bps": 0.0,
                },
            }
        )
        self.assertEqual(result["mode"], "PAPER_ONLY")
        self.assertEqual(result["result"]["metrics"]["trade_count"], 1)
        self.assertTrue(all(value is False for value in result["authority"].values()))


if __name__ == "__main__":
    unittest.main()
