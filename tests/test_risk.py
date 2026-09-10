import math
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

    def test_non_finite_runtime_inputs_fail_closed(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            result = size_long_trade(
                equity_usd=value,
                entry_price=100,
                stop_price=99,
            )
            self.assertFalse(result.approved)
            self.assertEqual(result.reason, "non_finite_risk_input")

            result = size_long_trade(
                equity_usd=100,
                entry_price=value,
                stop_price=99,
            )
            self.assertFalse(result.approved)
            self.assertEqual(result.reason, "non_finite_risk_input")

            result = size_long_trade(
                equity_usd=100,
                entry_price=100,
                stop_price=99,
                realized_daily_r=value,
            )
            self.assertFalse(result.approved)
            self.assertEqual(result.reason, "non_finite_risk_input")

    def test_non_finite_or_invalid_config_is_rejected(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                RiskConfig(risk_fraction_per_trade=value)
            with self.assertRaises(ValueError):
                RiskConfig(max_leverage=value)
            with self.assertRaises(ValueError):
                RiskConfig(daily_loss_limit_r=value)
        with self.assertRaises(ValueError):
            RiskConfig(risk_fraction_per_trade=0)
        with self.assertRaises(ValueError):
            RiskConfig(max_new_trades_per_day=0)

    def test_negative_trade_count_fails_closed(self) -> None:
        result = size_long_trade(
            equity_usd=100,
            entry_price=100,
            stop_price=99,
            new_trades_today=-1,
        )
        self.assertFalse(result.approved)
        self.assertEqual(result.reason, "invalid_trade_count")


if __name__ == "__main__":
    unittest.main()
