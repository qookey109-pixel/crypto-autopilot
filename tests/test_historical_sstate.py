from __future__ import annotations

import unittest

from crypto_autopilot.historical_sstate import (
    HistoricalSStateConflictError,
    HistoricalSStateNotAvailableError,
    HistoricalSStatePoint,
    HistoricalSStateReplayProvider,
)
from crypto_autopilot.models import SStateContext


HOUR = 3_600_000


def point(
    symbol: str,
    bar_hour: int,
    *,
    available_hour: int | None = None,
    state: str = "S3",
    probability: float | None = 0.7,
    samples: int = 100,
    source_ref: str | None = None,
) -> HistoricalSStatePoint:
    return HistoricalSStatePoint(
        symbol=symbol,
        bar_time_ms=bar_hour * HOUR,
        available_at_ms=(available_hour if available_hour is not None else bar_hour + 4) * HOUR,
        context=SStateContext(state=state, probability=probability, samples=samples, available=True),
        source_ref=source_ref or f"fixture:{symbol}:{bar_hour}",
    )


class HistoricalSStateReplayTest(unittest.TestCase):
    def test_exact_bar_context_is_hidden_until_recorded_availability(self) -> None:
        item = point("BTC_USDT_PERP", 0, available_hour=4)
        replay = HistoricalSStateReplayProvider([item])

        with self.assertRaises(HistoricalSStateNotAvailableError):
            replay.get_context_for_bar("BTC_USDT_PERP", 0, as_of_ms=4 * HOUR - 1)

        self.assertEqual(
            replay.get_context_for_bar("BTC_USDT_PERP", 0, as_of_ms=4 * HOUR),
            item.context,
        )

    def test_missing_exact_bar_does_not_carry_prior_state_forward(self) -> None:
        replay = HistoricalSStateReplayProvider([point("BTC_USDT_PERP", 0)])
        with self.assertRaises(HistoricalSStateNotAvailableError):
            replay.get_context_for_bar("BTC_USDT_PERP", 4 * HOUR, as_of_ms=8 * HOUR)

    def test_conflicting_authority_for_same_bar_is_rejected(self) -> None:
        with self.assertRaises(HistoricalSStateConflictError):
            HistoricalSStateReplayProvider(
                [
                    point("BTC_USDT_PERP", 0, state="S3", source_ref="a"),
                    point("BTC_USDT_PERP", 0, state="S1", source_ref="b"),
                ]
            )

    def test_identical_duplicate_authority_is_deduplicated(self) -> None:
        item = point("BTC_USDT_PERP", 0)
        replay = HistoricalSStateReplayProvider([item, item])
        self.assertEqual(replay.points, (item,))

    def test_available_points_are_deterministic_and_sorted(self) -> None:
        later = point("ETH_USDT_PERP", 4, available_hour=8)
        first = point("BTC_USDT_PERP", 0, available_hour=4)
        replay = HistoricalSStateReplayProvider([later, first])
        self.assertEqual(replay.available_points_as_of(4 * HOUR), (first,))
        self.assertEqual(replay.available_points_as_of(8 * HOUR), (first, later))

    def test_probability_and_availability_timestamps_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            point("BTC_USDT_PERP", 0, probability=1.1)

        with self.assertRaises(ValueError):
            HistoricalSStatePoint(
                symbol="BTC_USDT_PERP",
                bar_time_ms=4 * HOUR,
                available_at_ms=3 * HOUR,
                context=SStateContext(state="S3", probability=0.7, samples=100),
                source_ref="bad-time",
            )

    def test_replay_does_not_change_or_recompute_context(self) -> None:
        context = SStateContext(state="S0.5", probability=0.63, samples=77, available=True)
        item = HistoricalSStatePoint(
            symbol="SOL_USDT_PERP",
            bar_time_ms=0,
            available_at_ms=4 * HOUR,
            context=context,
            source_ref="frozen-sstate-output",
        )
        replay = HistoricalSStateReplayProvider([item])
        self.assertIs(replay.get_context_for_bar("SOL_USDT_PERP", 0, as_of_ms=4 * HOUR), context)


if __name__ == "__main__":
    unittest.main()
