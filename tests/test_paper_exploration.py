from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.backtest import LongTradePlan
from crypto_autopilot.models import Candle
from crypto_autopilot.paper.exploration import (
    PaperExplorationConfig,
    run_paper_exploration,
)


ROOT = Path(__file__).resolve().parents[1]


def candles() -> tuple[Candle, ...]:
    return (
        Candle(0, 100.0, 101.0, 99.0, 100.0, 10.0),
        Candle(60_000, 100.0, 111.0, 99.0, 110.0, 10.0),
    )


class PaperExplorationTests(unittest.TestCase):
    def test_repository_config_matches_safe_replay_contract(self) -> None:
        payload = json.loads(
            (ROOT / "config" / "paper_exploration_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["status"], "PREPARED_LOCAL_REPLAY_ONLY")
        parsed = PaperExplorationConfig(**payload["limits"])
        self.assertEqual(parsed.max_samples_per_utc_day, 12)
        self.assertTrue(
            all(value is False for value in payload["authority"].values())
        )

    def test_overlapping_symbols_produce_independent_samples(self) -> None:
        symbols = ("AAA", "BBB", "CCC")
        result = run_paper_exploration(
            candles_by_symbol={symbol: candles() for symbol in symbols},
            plans=tuple(
                LongTradePlan(f"plan-{symbol}", symbol, 0, 95.0, 110.0)
                for symbol in symbols
            ),
            config=PaperExplorationConfig(
                max_samples_per_utc_day=12,
                max_samples_per_symbol_per_utc_day=2,
            ),
        )
        self.assertEqual(result["sample_count"], 3)
        self.assertTrue(
            result["interpretation"]["independent_samples_not_portfolio_equity"]
        )
        self.assertFalse(result["authority"]["live_trading_authorized"])

    def test_daily_and_symbol_caps_are_enforced(self) -> None:
        result = run_paper_exploration(
            candles_by_symbol={"AAA": candles(), "BBB": candles()},
            plans=(
                LongTradePlan("a-1", "AAA", 0, 95.0, 110.0),
                LongTradePlan("a-2", "AAA", 1, 95.0, 110.0),
                LongTradePlan("b-1", "BBB", 2, 95.0, 110.0),
            ),
            config=PaperExplorationConfig(
                max_samples_per_utc_day=2,
                max_samples_per_symbol_per_utc_day=1,
            ),
        )
        self.assertEqual(result["sample_count"], 2)
        reasons = {item[1] for item in result["rejected_plans"]}
        self.assertIn("exploration_symbol_daily_sample_gate", reasons)

    def test_risk_and_leverage_bounds_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "0.5%"):
            PaperExplorationConfig(risk_fraction_per_sample=0.01)
        with self.assertRaisesRegex(ValueError, "safe bound"):
            PaperExplorationConfig(max_leverage=4.0)


if __name__ == "__main__":
    unittest.main()
