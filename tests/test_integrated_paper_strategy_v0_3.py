from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from crypto_autopilot.integrated_paper_strategy_v0_2 import (
    IntegratedCandidate,
    IntegratedMarket,
    ResearchContext,
)
from crypto_autopilot.integrated_paper_strategy_v0_3 import (
    run_integrated_evidence_lanes_v0_3,
    run_integrated_portfolio_replay_v0_3,
)
from crypto_autopilot.models import Candle
from crypto_autopilot.paper_long_short_challenger_v0_2 import (
    DirectionalCandidate,
    DirectionalPlan,
)


ROOT = Path(__file__).resolve().parents[1]
STEP = 900_000


def _config() -> dict[str, object]:
    return json.loads(
        (ROOT / "config" / "integrated_paper_strategy_v0_3.json").read_text(
            encoding="utf-8"
        )
    )


def _candidate(
    plan_id: str,
    *,
    signal_time_ms: int,
    stop_price: float = 98.0,
    stop_distance_atr: float = 1.5,
    stop_source: str = "DIRECTIONAL_ATR_BUFFERED",
) -> IntegratedCandidate:
    plan = DirectionalPlan(
        plan_id=plan_id,
        symbol="BTC_USDT_PERP",
        side="LONG",
        signal_time_ms=signal_time_ms,
        stop_price=stop_price,
        target_price=104.0,
    )
    directional = DirectionalCandidate(
        plan=plan,
        score=82.0,
        eligible=True,
        reasons=("eligible_paper_challenger",),
        reference_price=100.0,
        features=(("adx14", 30.0),),
    )
    return IntegratedCandidate(
        market=IntegratedMarket(
            symbol="BTC_USDT_PERP",
            asset_class="crypto",
            provider="pionex_public_futures",
            status="TRADING",
            intervals=("15M", "60M", "4H", "8H", "1D"),
            spread_bps=5.0,
        ),
        directional=directional,
        regime="TREND_UP",
        volatility_regime="NORMAL",
        sstate_bridge_mode="FORMAL_V0_1_DECISION_REQUIRED",
        formal_strategy_decision=None,
        research_context=ResearchContext(),
        stop_source=stop_source,
        stop_distance_atr=stop_distance_atr,
        eligible=True,
        reasons=("eligible_integrated_paper_candidate",),
    )


def _candles() -> tuple[Candle, ...]:
    return (
        Candle(STEP, 100.0, 101.0, 99.0, 100.5, 10.0),
        Candle(2 * STEP, 100.5, 102.5, 100.0, 102.0, 10.0),
        Candle(3 * STEP, 102.0, 104.5, 101.5, 104.0, 10.0),
    )


class IntegratedPaperStrategyV03Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = _config()

    def test_portfolio_and_independent_signal_lanes_are_not_blended(self) -> None:
        candidates = (
            _candidate("first", signal_time_ms=0),
            _candidate("overlap", signal_time_ms=STEP),
        )
        result = run_integrated_evidence_lanes_v0_3(
            candidates=candidates,
            candles_by_symbol={"BTC_USDT_PERP": _candles()},
            config=self.config,
        )
        self.assertEqual(result["portfolio"]["metrics"]["trade_count"], 1)
        self.assertEqual(
            result["independentSignalExploration"]["sampleMetrics"]["sample_count"],
            2,
        )
        self.assertFalse(result["metricsMayBeCombined"])
        self.assertTrue(result["portfolio"]["portfolioPerformanceValid"])
        self.assertFalse(
            result["independentSignalExploration"]["portfolioPerformanceValid"]
        )
        self.assertFalse(
            result["independentSignalExploration"][
                "aggregatePnlMayBeReportedAsPortfolioPnl"
            ]
        )

    def test_reward_risk_and_stop_distance_distributions_are_reported(self) -> None:
        result = run_integrated_portfolio_replay_v0_3(
            candidates=(_candidate("rr", signal_time_ms=0, stop_distance_atr=2.5),),
            candles_by_symbol={"BTC_USDT_PERP": _candles()},
            config=self.config,
        )
        diagnostics = result["rewardRiskDiagnostics"]
        self.assertEqual(diagnostics["stopDistanceAtr"]["executedTrades"]["p50"], 2.5)
        self.assertEqual(diagnostics["plannedRewardRisk"]["distribution"]["count"], 1)
        self.assertIn("1.20", diagnostics["plannedRewardRisk"]["fractionBelow"])
        self.assertEqual(
            diagnostics["byStopSource"]["DIRECTIONAL_ATR_BUFFERED"]["trade_count"],
            1,
        )

    def test_leverage_rejected_signal_quality_is_retained(self) -> None:
        result = run_integrated_portfolio_replay_v0_3(
            candidates=(
                _candidate(
                    "tight",
                    signal_time_ms=0,
                    stop_price=99.9,
                    stop_distance_atr=0.1,
                    stop_source="EMA20_BUFFERED",
                ),
            ),
            candles_by_symbol={"BTC_USDT_PERP": _candles()},
            config=self.config,
        )
        quality = result["rewardRiskDiagnostics"]["leverageRejectedCandidateQuality"]
        self.assertEqual(quality["count"], 1)
        self.assertEqual(quality["averageTechnicalScore"], 82.0)
        self.assertEqual(quality["byStopSource"], {"EMA20_BUFFERED": 1})

    def test_v03_remains_research_only(self) -> None:
        self.assertEqual(self.config["status"], "PREPARED_LOCAL_REPLAY_ONLY")
        self.assertTrue(all(value is False for value in self.config["authority"].values()))

    def test_prepared_receipt_hashes_current_protocol_files(self) -> None:
        receipt = json.loads(
            (
                ROOT
                / "research"
                / "receipts"
                / "2026-08-26-integrated-paper-strategy-v0-3-promotion-v0-2-prepared.json"
            ).read_text(encoding="utf-8")
        )
        for relative_path, expected_hash in receipt["sha256"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest(),
                expected_hash,
            )
        self.assertFalse(receipt["execution_boundary"]["replacement_holdout_accessed"])
        self.assertFalse(receipt["execution_boundary"]["live_trading_authorized"])


if __name__ == "__main__":
    unittest.main()
