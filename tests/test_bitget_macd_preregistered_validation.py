import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.bitget_macd import BitgetMacdResearchConfig
from crypto_autopilot.research.bitget_macd_validation import (
    BitgetMacdValidationPlan,
    build_preregistered_windows,
    plan_sha256,
    run_preregistered_validation,
)


FIFTEEN_MINUTES_MS = 15 * 60 * 1000


def _source(bar_count_30m: int) -> list[Candle]:
    rows = []
    price = 100.0
    for index in range(bar_count_30m * 2):
        wave = ((index % 24) - 12) * 0.08
        close = max(10.0, price + wave + (0.03 if index % 7 else -0.02))
        high = max(price, close) * 1.002
        low = min(price, close) * 0.998
        rows.append(
            Candle(
                time_ms=index * FIFTEEN_MINUTES_MS,
                open=price,
                high=high,
                low=low,
                close=close,
                volume=10.0 + index % 5,
            )
        )
        price = close
    return rows


class BitgetMacdPreregisteredValidationTests(unittest.TestCase):
    def test_temporal_windows_are_disjoint_and_confirmation_is_last(self) -> None:
        plan = BitgetMacdValidationPlan(
            development_folds=2,
            min_30m_bars_per_window=50,
            top_k=1,
        )
        development, confirmation = build_preregistered_windows(_source(300), plan=plan)

        self.assertEqual(len(development), 2)
        self.assertLessEqual(development[0].end_time_ms, development[1].start_time_ms)
        self.assertLessEqual(development[-1].end_time_ms, confirmation.start_time_ms)
        self.assertEqual(confirmation.phase, "CONFIRMATION")
        self.assertFalse(plan.confirmation_can_change_parameters)
        self.assertFalse(plan.formal_project_holdout_accessed)

    def test_plan_hash_is_deterministic(self) -> None:
        self.assertEqual(plan_sha256(), plan_sha256())
        self.assertEqual(len(plan_sha256()), 64)

    def test_end_to_end_small_grid_keeps_confirmation_out_of_selection(self) -> None:
        plan = BitgetMacdValidationPlan(
            development_folds=2,
            min_30m_bars_per_window=50,
            top_k=1,
            min_trades_per_development_window=1,
            confirmation_slippage_stress_bps_per_side=(2.0, 5.0),
        )
        configs = (
            BitgetMacdResearchConfig(
                fast_period=2,
                slow_period=5,
                signal_period=2,
                stop_loss_fraction=0.05,
                leverage=1.0,
                margin_fraction=0.2,
                fluctuation_lookback=0,
                min_fluctuation_fraction=0.0,
            ),
            BitgetMacdResearchConfig(
                fast_period=3,
                slow_period=7,
                signal_period=2,
                stop_loss_fraction=0.05,
                leverage=1.0,
                margin_fraction=0.2,
                fluctuation_lookback=0,
                min_fluctuation_fraction=0.0,
            ),
        )

        result = run_preregistered_validation(
            candles_15m=_source(300),
            configs=configs,
            plan=plan,
        )

        self.assertEqual(result.candidate_count, 2)
        self.assertEqual(len(result.selected_development_candidates), 1)
        self.assertEqual(len(result.confirmation_results), 2)
        self.assertFalse(result.confirmation_used_for_selection)
        self.assertFalse(result.formal_project_holdout_accessed)
        self.assertTrue(result.paper_only)


if __name__ == "__main__":
    unittest.main()
