from __future__ import annotations

import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.causal_prefix_replay_v0_1 import replay_60m_at_cutoff

HOUR = 3_600_000


def sample(count: int) -> list[Candle]:
    rows = []
    for index in range(count):
        close = 100.0 + index * 0.1 + (index % 7) * 0.2
        rows.append(Candle(index * HOUR, close, close + 1, close - 1, close, 100.0 + index))
    return rows


class CausalPrefixReplayTests(unittest.TestCase):
    def test_future_candles_do_not_change_historical_snapshot(self) -> None:
        original = sample(100)
        changed = list(original[:70])
        for row in original[70:]:
            changed.append(Candle(row.time_ms, 1000, 1001, 999, 1000, 500))
        cutoff = 70 * HOUR + HOUR // 2
        before = replay_60m_at_cutoff(original, cutoff)
        after = replay_60m_at_cutoff(changed, cutoff)
        self.assertEqual(before, after)
        self.assertEqual(before["source"]["last_closed_bar_start_ms"], 69 * HOUR)
        self.assertEqual(before["source"]["candle_count"], 70)
        self.assertEqual(before["decision_cutoff_ms"], cutoff)

    def test_bar_becomes_available_only_at_close(self) -> None:
        rows = sample(80)
        before = replay_60m_at_cutoff(rows, 70 * HOUR - 1)
        after = replay_60m_at_cutoff(rows, 70 * HOUR)
        self.assertEqual(before["source"]["last_closed_bar_start_ms"], 68 * HOUR)
        self.assertEqual(after["source"]["last_closed_bar_start_ms"], 69 * HOUR)

    def test_gap_and_duplicate_fail_closed(self) -> None:
        rows = sample(80)
        for damaged in (rows[:30] + rows[31:], rows[:30] + [rows[29]] + rows[30:]):
            with self.subTest(length=len(damaged)), self.assertRaises(ValueError):
                replay_60m_at_cutoff(damaged, 70 * HOUR)

    def test_bad_closed_bar_numbers_fail_but_future_values_are_not_consumed(self) -> None:
        rows = sample(80)
        for value in (True, float("nan"), float("inf"), "100"):
            damaged = list(rows)
            row = damaged[30]
            damaged[30] = Candle(row.time_ms, row.open, row.high, row.low, row.close, value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                replay_60m_at_cutoff(damaged, 70 * HOUR)
        future = list(rows)
        row = future[75]
        future[75] = Candle(row.time_ms, row.open, row.high, row.low, row.close, True)
        self.assertEqual(
            replay_60m_at_cutoff(rows, 70 * HOUR),
            replay_60m_at_cutoff(future, 70 * HOUR),
        )

    def test_missing_latest_closed_bar_stops(self) -> None:
        with self.assertRaises(ValueError):
            replay_60m_at_cutoff(sample(70), 80 * HOUR)

    def test_insufficient_and_invalid_cutoff_stop(self) -> None:
        for cutoff in (0, True, -1):
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                replay_60m_at_cutoff(sample(80), cutoff)
        with self.assertRaises(ValueError):
            replay_60m_at_cutoff(sample(10), 10 * HOUR)

    def test_research_limits_remain_explicit(self) -> None:
        out = replay_60m_at_cutoff(sample(80), 70 * HOUR)
        self.assertEqual(out["status"], "RESEARCH_ONLY")
        self.assertFalse(out["source"]["externally_authenticated"])
        self.assertFalse(out["authority"]["strategy_qualification"])
        self.assertFalse(out["authority"]["paper_submission"])
        self.assertIsNone(out["costs"]["net_return"])
        self.assertEqual(out["timeframes"]["15M"], "UNKNOWN")
        self.assertEqual(out["timeframes"]["4H"], "UNKNOWN")
        self.assertLessEqual(out["technical"]["available_at_ms"], out["decision_cutoff_ms"])
        self.assertLessEqual(out["patterns"]["available_at_ms"], out["decision_cutoff_ms"])


if __name__ == "__main__":
    unittest.main()
