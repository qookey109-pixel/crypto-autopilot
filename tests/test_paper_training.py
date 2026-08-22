from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle
from crypto_autopilot.paper_training import REQUIRED_INTERVALS, run_paper_training_replay


ROOT = Path(__file__).resolve().parents[1]


def _aligned_candles(interval: str, *, count: int = 500) -> tuple[Candle, ...]:
    step = INTERVAL_MS[interval]
    end = (2_000_000_000_000 // INTERVAL_MS["1D"]) * INTERVAL_MS["1D"]
    start = end - count * step
    output = []
    for index in range(count):
        close = 100.0 + index * 0.08 + (index % 8) * 0.04
        output.append(
            Candle(
                time_ms=start + index * step,
                open=close - 0.03,
                high=close + 0.7,
                low=close - 0.7,
                close=close,
                volume=100.0 + index % 11,
            )
        )
    return tuple(output)


class PaperTrainingTests(unittest.TestCase):
    def test_replay_generates_auditable_paper_only_result(self) -> None:
        config = json.loads(
            (ROOT / "config" / "paper_training_v0_1.json").read_text(encoding="utf-8")
        )
        config = copy.deepcopy(config)
        config["candidate_thresholds"].update(
            {
                "minimum_trend_agreement": 0.0,
                "minimum_adx14": 0.0,
                "minimum_rsi14": 0.0,
                "maximum_rsi14": 100.0,
                "minimum_donchian_position": -10.0,
                "minimum_volume_zscore": -100.0,
                "minimum_efficiency_ratio": 0.0,
                "minimum_candidate_score": 0.0,
            }
        )
        candles = {interval: _aligned_candles(interval) for interval in REQUIRED_INTERVALS}
        result = run_paper_training_replay(
            run_id="unit-test",
            observed_at_utc="2033-05-18T03:33:20+00:00",
            candles_by_symbol_interval={"BTC_USDT_PERP": candles},
            funding_by_symbol={},
            live_microstructure={},
            live_derivatives={},
            config=config,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "PAPER_TRAINING_ONLY")
        self.assertGreater(result["candidateCount"], 0)
        self.assertGreater(result["eligibleCandidateCount"], 0)
        self.assertEqual(result["symbolCount"], 1)
        self.assertEqual(len(result["lineageFingerprint"]), 64)
        authority = result["authority"]
        self.assertTrue(authority["repositoryPaperBrokerAuthorized"])
        for key in (
            "formalTradePlanAuthorized",
            "pionexDemoAutomationAuthorized",
            "privateApiUsed",
            "r2ReadsPerformed",
            "r2WritesPerformed",
            "holdoutAccessed",
            "sourceSwitchAuthorized",
            "realMoneyOrderAuthorized",
            "liveTradingAuthorized",
        ):
            self.assertFalse(authority[key], key)
        self.assertTrue(
            all(item["action"] == "MANUAL_REVIEW_ONLY" for item in result["manualPionexDemoSamples"])
        )
        self.assertGreater(len(result["manualPionexDemoSamples"]), 0)
        self.assertLessEqual(len(result["manualPionexDemoSamples"]), 3)

    def test_missing_required_timeframe_fails_closed_for_symbol(self) -> None:
        config = json.loads(
            (ROOT / "config" / "paper_training_v0_1.json").read_text(encoding="utf-8")
        )
        candles = {interval: _aligned_candles(interval) for interval in REQUIRED_INTERVALS[:-1]}
        result = run_paper_training_replay(
            run_id="missing-timeframe",
            observed_at_utc="2033-05-18T03:33:20+00:00",
            candles_by_symbol_interval={"BTC_USDT_PERP": candles},
            funding_by_symbol={},
            live_microstructure={},
            live_derivatives={},
            config=config,
        )
        self.assertEqual(result["candidateCount"], 0)
        self.assertEqual(result["metrics"]["trade_count"], 0)


if __name__ == "__main__":
    unittest.main()
