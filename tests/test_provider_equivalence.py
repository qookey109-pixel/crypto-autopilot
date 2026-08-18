from __future__ import annotations

import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.provider_equivalence import (
    ProviderEquivalencePolicy,
    aggregate_provider_equivalence,
    compare_provider_pair,
)


def candles(count: int, step_ms: int, *, price_scale: float = 1.0, volume_scale: float = 1.0):
    output = []
    for index in range(count):
        base = 100.0 + index * 0.1 + (index % 7) * 0.03
        open_price = base
        close = base + (0.08 if index % 2 == 0 else -0.04)
        high = max(open_price, close) + 0.2
        low = min(open_price, close) - 0.2
        output.append(
            Candle(
                time_ms=index * step_ms,
                open=open_price * price_scale,
                high=high * price_scale,
                low=low * price_scale,
                close=close * price_scale,
                volume=(10.0 + index) * volume_scale,
            )
        )
    return tuple(output)


class ProviderEquivalenceTests(unittest.TestCase):
    def test_identical_15m_pair_passes_even_when_volume_differs(self) -> None:
        left = candles(672, 15 * 60 * 1000, volume_scale=1.0)
        right = tuple(
            Candle(c.time_ms, c.open, c.high, c.low, c.close, c.volume * 100.0)
            for c in left
        )
        result = compare_provider_pair(
            pionex_symbol="BTC_USDT_PERP",
            binance_symbol="BTCUSDT",
            interval="15M",
            pionex_candles=left,
            binance_candles=right,
        )
        self.assertEqual(result.status, "PASS")
        self.assertFalse(result.volume_compared)
        self.assertEqual(result.median_ohlc_bps, 0.0)

    def test_small_price_basis_can_enter_review_without_fail(self) -> None:
        left = candles(672, 15 * 60 * 1000)
        # 15 bps uniform basis: above 10 bps median PASS ceiling but below 25 bps REVIEW ceiling.
        right = candles(672, 15 * 60 * 1000, price_scale=1.0015)
        result = compare_provider_pair(
            pionex_symbol="ETH_USDT_PERP",
            binance_symbol="ETHUSDT",
            interval="15M",
            pionex_candles=left,
            binance_candles=right,
        )
        self.assertEqual(result.status, "REVIEW")
        self.assertIn("median_ohlc_bps_review", result.reasons)

    def test_large_basis_fails(self) -> None:
        left = candles(672, 15 * 60 * 1000)
        right = candles(672, 15 * 60 * 1000, price_scale=1.01)
        result = compare_provider_pair(
            pionex_symbol="SOL_USDT_PERP",
            binance_symbol="SOLUSDT",
            interval="15M",
            pionex_candles=left,
            binance_candles=right,
        )
        self.assertEqual(result.status, "FAIL")

    def test_timestamp_mismatch_is_hard_fail(self) -> None:
        left = candles(672, 15 * 60 * 1000)
        right = left[:-1]
        result = compare_provider_pair(
            pionex_symbol="BTC_USDT_PERP",
            binance_symbol="BTCUSDT",
            interval="15M",
            pionex_candles=left,
            binance_candles=right,
        )
        self.assertEqual(result.status, "FAIL")
        self.assertFalse(result.timestamp_exact)
        self.assertEqual(result.missing_in_binance, 1)

    def test_60m_frozen_setup_state_is_compared(self) -> None:
        left = candles(168, 60 * 60 * 1000)
        right = tuple(
            Candle(c.time_ms, c.open, c.high, c.low, c.close, c.volume * 3.0)
            for c in left
        )
        result = compare_provider_pair(
            pionex_symbol="BTC_USDT_PERP",
            binance_symbol="BTCUSDT",
            interval="60M",
            pionex_candles=left,
            binance_candles=right,
        )
        self.assertEqual(result.status, "PASS")
        self.assertIsNotNone(result.setup_60m_ready_bars)
        self.assertGreaterEqual(result.setup_60m_ready_bars or 0, 100)
        self.assertEqual(result.setup_60m_agreement, 1.0)

    def test_4h_minimum_row_gate(self) -> None:
        left = candles(39, 4 * 60 * 60 * 1000)
        result = compare_provider_pair(
            pionex_symbol="BTC_USDT_PERP",
            binance_symbol="BTCUSDT",
            interval="4H",
            pionex_candles=left,
            binance_candles=left,
        )
        self.assertEqual(result.status, "FAIL")
        self.assertIn("insufficient_rows_min_40", result.reasons)

    def test_aggregate_never_authorizes_source_switch_in_v0_1(self) -> None:
        base = compare_provider_pair(
            pionex_symbol="BTC_USDT_PERP",
            binance_symbol="BTCUSDT",
            interval="15M",
            pionex_candles=candles(672, 15 * 60 * 1000),
            binance_candles=candles(672, 15 * 60 * 1000),
        )
        results = []
        for index in range(45):
            results.append(
                type(base)(
                    pionex_symbol=f"P{index}",
                    binance_symbol=f"B{index}",
                    interval=("15M", "60M", "4H")[index % 3],
                    pionex_rows=base.pionex_rows,
                    binance_rows=base.binance_rows,
                    timestamp_exact=True,
                    missing_in_pionex=0,
                    missing_in_binance=0,
                    median_ohlc_bps=0.0,
                    p95_open_close_bps=0.0,
                    p95_high_low_bps=0.0,
                    return_direction_agreement=1.0,
                    setup_60m_ready_bars=100 if index % 3 == 1 else None,
                    setup_60m_agreement=1.0 if index % 3 == 1 else None,
                    status="PASS",
                    reasons=(),
                )
            )
        aggregate = aggregate_provider_equivalence(results)
        self.assertEqual(aggregate.status, "PASS")
        self.assertFalse(aggregate.source_switch_authorized)
        self.assertEqual(
            aggregate.full_strategy_signal_equivalence_status,
            "DEFERRED_UNDEFINED_STRATEGY_RULES",
        )

    def test_aggregate_review_fraction_and_fail_behavior(self) -> None:
        policy = ProviderEquivalencePolicy(max_review_fraction_for_aggregate_review=0.20)
        base = compare_provider_pair(
            pionex_symbol="BTC_USDT_PERP",
            binance_symbol="BTCUSDT",
            interval="15M",
            pionex_candles=candles(672, 15 * 60 * 1000),
            binance_candles=candles(672, 15 * 60 * 1000),
        )
        results = []
        for index in range(45):
            status = "REVIEW" if index < 9 else "PASS"
            results.append(
                type(base)(
                    pionex_symbol=f"P{index}",
                    binance_symbol=f"B{index}",
                    interval="15M",
                    pionex_rows=672,
                    binance_rows=672,
                    timestamp_exact=True,
                    missing_in_pionex=0,
                    missing_in_binance=0,
                    median_ohlc_bps=0.0,
                    p95_open_close_bps=0.0,
                    p95_high_low_bps=0.0,
                    return_direction_agreement=1.0,
                    setup_60m_ready_bars=None,
                    setup_60m_agreement=None,
                    status=status,
                    reasons=(),
                )
            )
        self.assertEqual(aggregate_provider_equivalence(results, policy=policy).status, "REVIEW")
        results[0] = type(results[0])(**{**results[0].__dict__, "status": "FAIL"}) if hasattr(results[0], "__dict__") else type(results[0])(
            pionex_symbol=results[0].pionex_symbol,
            binance_symbol=results[0].binance_symbol,
            interval=results[0].interval,
            pionex_rows=results[0].pionex_rows,
            binance_rows=results[0].binance_rows,
            timestamp_exact=results[0].timestamp_exact,
            missing_in_pionex=results[0].missing_in_pionex,
            missing_in_binance=results[0].missing_in_binance,
            median_ohlc_bps=results[0].median_ohlc_bps,
            p95_open_close_bps=results[0].p95_open_close_bps,
            p95_high_low_bps=results[0].p95_high_low_bps,
            return_direction_agreement=results[0].return_direction_agreement,
            setup_60m_ready_bars=results[0].setup_60m_ready_bars,
            setup_60m_agreement=results[0].setup_60m_agreement,
            status="FAIL",
            reasons=results[0].reasons,
        )
        self.assertEqual(aggregate_provider_equivalence(results, policy=policy).status, "FAIL")


if __name__ == "__main__":
    unittest.main()
