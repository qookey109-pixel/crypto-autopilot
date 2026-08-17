import unittest

from crypto_autopilot.risk import RiskConfig, size_long_trade


class RiskTests(unittest.TestCase):
    def test_one_percent_risk_sizes_from_stop_distance(self) -> None:
        result = size_long_trade(equity_usd=100, entry_price=100, stop_price=99.5)
        self.assertTrue(result.approved)
        self.assertAlmostEqual(result.risk_usd, 1.0)
        self.assertAlmostEqual(result.notional_usd, 200.0)
        self.assertAlmostEqual(result.required_leverage, 2.0)

    def test_trade_is_rejected_when_required_leverage_exceeds_cap(self) -> None:
        result = size_long_trade(equity_usd=100, entry_price=100, stop_price=99.8)
        self.assertFalse(result.approved)
        self.assertEqual(result.reason, "required_leverage_exceeds_cap")

    def test_daily_loss_gate(self) -> None:
        result = size_long_trade(
            equity_usd=100,
            entry_price=100,
            stop_price=99,
            realized_daily_r=-3.0,
        )
        self.assertFalse(result.approved)
        self.assertEqual(result.reason, "daily_loss_gate")

    def test_daily_trade_count_gate(self) -> None:
        result = size_long_trade(
            equity_usd=100,
            entry_price=100,
            stop_price=99,
            new_trades_today=3,
            config=RiskConfig(max_new_trades_per_day=3),
        )
        self.assertFalse(result.approved)
        self.assertEqual(result.reason, "daily_trade_count_gate")


if __name__ == "__main__":
    unittest.main()
