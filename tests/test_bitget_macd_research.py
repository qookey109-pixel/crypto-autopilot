import unittest

from crypto_autopilot.bitget_macd_research import (
    BitgetMacdResearchConfig,
    THIRTY_MINUTES_MS,
    aggregate_15m_to_30m,
    default_bitget_macd_candidate_grid,
    macd_series,
    run_bitget_macd_long_30m_research,
)
from crypto_autopilot.models import Candle


FIFTEEN_MINUTES_MS = 15 * 60 * 1000


def _candles_15m_from_30m_closes(closes: list[float]) -> list[Candle]:
    output: list[Candle] = []
    previous = closes[0]
    for index, close in enumerate(closes):
        first_time = index * THIRTY_MINUTES_MS
        midpoint = (previous + close) / 2.0
        first_high = max(previous, midpoint) * 1.001
        first_low = min(previous, midpoint) * 0.999
        second_high = max(midpoint, close) * 1.001
        second_low = min(midpoint, close) * 0.999
        output.append(
            Candle(first_time, previous, first_high, first_low, midpoint, 10.0)
        )
        output.append(
            Candle(
                first_time + FIFTEEN_MINUTES_MS,
                midpoint,
                second_high,
                second_low,
                close,
                12.0,
            )
        )
        previous = close
    return output


class BitgetMacdResearchTests(unittest.TestCase):
    def test_aggregate_15m_to_30m_is_canonical_and_lossless_for_ohlcv(self) -> None:
        candles = [
            Candle(0, 100.0, 102.0, 99.0, 101.0, 10.0),
            Candle(FIFTEEN_MINUTES_MS, 101.0, 103.0, 100.0, 102.0, 12.0),
            Candle(THIRTY_MINUTES_MS, 102.0, 104.0, 101.0, 103.0, 9.0),
            Candle(
                THIRTY_MINUTES_MS + FIFTEEN_MINUTES_MS,
                103.0,
                105.0,
                102.0,
                104.0,
                11.0,
            ),
        ]

        result = aggregate_15m_to_30m(candles)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].time_ms, 0)
        self.assertEqual(result[0].open, 100.0)
        self.assertEqual(result[0].high, 103.0)
        self.assertEqual(result[0].low, 99.0)
        self.assertEqual(result[0].close, 102.0)
        self.assertEqual(result[0].volume, 22.0)

    def test_aggregation_fails_closed_on_interior_gap(self) -> None:
        candles = [
            Candle(0, 100.0, 101.0, 99.0, 100.0, 1.0),
            Candle(THIRTY_MINUTES_MS, 100.0, 101.0, 99.0, 100.0, 1.0),
        ]

        with self.assertRaisesRegex(ValueError, "strictly contiguous"):
            aggregate_15m_to_30m(candles)

    def test_long_signal_enters_on_next_30m_open_without_lookahead(self) -> None:
        closes = [
            120.0,
            118.0,
            116.0,
            114.0,
            112.0,
            110.0,
            108.0,
            106.0,
            104.0,
            102.0,
            100.0,
            101.0,
            103.0,
            106.0,
            110.0,
            115.0,
            121.0,
            125.0,
            127.0,
            126.0,
            123.0,
            119.0,
            114.0,
            108.0,
            103.0,
        ]
        source = _candles_15m_from_30m_closes(closes)
        candles_30m = aggregate_15m_to_30m(source)
        macd, signal = macd_series(
            candles_30m, fast_period=2, slow_period=5, signal_period=2
        )
        cross_indexes = [
            index
            for index in range(1, len(candles_30m) - 1)
            if macd[index - 1] is not None
            and signal[index - 1] is not None
            and macd[index] is not None
            and signal[index] is not None
            and macd[index - 1] <= signal[index - 1]
            and macd[index] > signal[index]
        ]
        self.assertTrue(cross_indexes)
        expected_entry_time = candles_30m[cross_indexes[0] + 1].time_ms
        config = BitgetMacdResearchConfig(
            fast_period=2,
            slow_period=5,
            signal_period=2,
            stop_loss_fraction=0.20,
            leverage=1.0,
            margin_fraction=0.20,
            fluctuation_lookback=0,
            min_fluctuation_fraction=0.0,
            taker_fee_bps_per_side=0.0,
            slippage_bps_per_side=0.0,
        )

        result = run_bitget_macd_long_30m_research(
            candles_15m=source, config=config, initial_equity_usd=10_000.0
        )

        self.assertGreaterEqual(result.metrics.trade_count, 1)
        self.assertEqual(result.trades[0].entry_time_ms, expected_entry_time)
        self.assertIn(
            result.trades[0].exit_reason,
            {"macd_death_cross_next_open", "stop", "stop_gap", "end_of_data"},
        )
        self.assertIs(result.paper_only, True)
        self.assertIs(result.bitget_filter_formula_verified, False)

    def test_risk_cap_reduces_baseline_20_percent_margin_at_3x(self) -> None:
        closes = [
            120.0,
            118.0,
            116.0,
            114.0,
            112.0,
            110.0,
            108.0,
            106.0,
            104.0,
            102.0,
            100.0,
            101.0,
            103.0,
            106.0,
            110.0,
            115.0,
            121.0,
            125.0,
            127.0,
            126.0,
            123.0,
            119.0,
            114.0,
            108.0,
            103.0,
        ]
        source = _candles_15m_from_30m_closes(closes)
        common = dict(
            fast_period=2,
            slow_period=5,
            signal_period=2,
            stop_loss_fraction=0.05,
            leverage=3.0,
            margin_fraction=0.20,
            fluctuation_lookback=0,
            min_fluctuation_fraction=0.0,
            taker_fee_bps_per_side=0.0,
            slippage_bps_per_side=0.0,
        )
        baseline = run_bitget_macd_long_30m_research(
            candles_15m=source,
            config=BitgetMacdResearchConfig(**common),
            initial_equity_usd=10_000.0,
        )
        capped = run_bitget_macd_long_30m_research(
            candles_15m=source,
            config=BitgetMacdResearchConfig(**common, risk_cap_fraction=0.01),
            initial_equity_usd=10_000.0,
        )

        self.assertGreaterEqual(baseline.metrics.trade_count, 1)
        self.assertGreaterEqual(capped.metrics.trade_count, 1)
        self.assertAlmostEqual(baseline.trades[0].notional_usd, 6_000.0)
        self.assertAlmostEqual(capped.trades[0].notional_usd, 2_000.0)

    def test_high_fluctuation_filter_can_block_signal(self) -> None:
        closes = [100.0 - index * 0.2 for index in range(12)] + [
            98.0,
            99.0,
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            106.0,
            105.0,
            104.0,
        ]
        source = _candles_15m_from_30m_closes(closes)
        config = BitgetMacdResearchConfig(
            fast_period=2,
            slow_period=5,
            signal_period=2,
            stop_loss_fraction=0.10,
            leverage=1.0,
            margin_fraction=0.20,
            fluctuation_lookback=5,
            min_fluctuation_fraction=0.50,
        )

        result = run_bitget_macd_long_30m_research(candles_15m=source, config=config)

        self.assertEqual(result.metrics.trade_count, 0)

    def test_default_candidate_grid_is_bounded_and_contains_user_baseline(self) -> None:
        grid = default_bitget_macd_candidate_grid()

        self.assertEqual(len(grid), 2304)
        self.assertTrue(
            any(
                config.fast_period == 12
                and config.slow_period == 26
                and config.signal_period == 9
                and config.stop_loss_fraction == 0.05
                and config.leverage == 3.0
                and config.margin_fraction == 0.20
                and config.risk_cap_fraction is None
                and config.fluctuation_lookback == 5
                and config.min_fluctuation_fraction == 0.012
                for config in grid
            )
        )


if __name__ == "__main__":
    unittest.main()
