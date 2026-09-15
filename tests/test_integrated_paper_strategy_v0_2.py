from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from crypto_autopilot.integrated_paper_strategy_v0_2 import (
    IntegratedCandidate,
    IntegratedMarket,
    ResearchContext,
    build_integrated_candidates,
    run_integrated_paper_replay,
)
from crypto_autopilot.models import (
    Candle,
    EntryFeatures,
    OpportunityInput,
    SStateContext,
    SetupFeatures,
)
from crypto_autopilot.paper_long_short_challenger_v0_2 import (
    DirectionalCandidate,
    DirectionalPlan,
)


ROOT = Path(__file__).resolve().parents[1]
STEP = 900_000


def _config() -> dict[str, object]:
    return json.loads(
        (ROOT / "config" / "integrated_paper_strategy_v0_2.json").read_text(
            encoding="utf-8"
        )
    )


def _opportunity(*, probability: float = 0.68, good_features: bool = True) -> OpportunityInput:
    return OpportunityInput(
        symbol="BTC_USDT_PERP",
        sstate=SStateContext("S3", probability, 120),
        setup=SetupFeatures(*(good_features for _ in range(4))),
        entry=EntryFeatures(*(good_features for _ in range(4))),
        reward_risk=2.0,
        liquidity_ok=True,
        funding_ok=True,
    )


def _technical(side: str) -> SimpleNamespace:
    long = side == "LONG"
    return SimpleNamespace(
        bar_time_ms=0,
        available_at_ms=STEP,
        ready_v0_2=True,
        ema20=101.0 if long else 99.0,
        ema50=100.0,
        ema200=99.0 if long else 101.0,
        ema20_slope=0.2 if long else -0.2,
        close=102.0 if long else 98.0,
        atr14=2.0,
        rsi14=60.0 if long else 40.0,
        macd_histogram=0.3 if long else -0.3,
    )


def _advanced(side: str) -> SimpleNamespace:
    long = side == "LONG"
    return SimpleNamespace(
        ready=True,
        adx14=30.0,
        plus_di14=30.0 if long else 15.0,
        minus_di14=15.0 if long else 30.0,
        vwap_distance_fraction=0.02 if long else -0.02,
        volume_zscore20=1.0,
        donchian_position20=0.9 if long else 0.1,
        atr_percentile100=0.5,
        kaufman_efficiency_ratio10=0.6,
    )


def _market(*, asset_class: str = "crypto", session: bool = False) -> IntegratedMarket:
    return IntegratedMarket(
        symbol="BTC_USDT_PERP" if asset_class == "crypto" else "TSLA_USDT_PERP",
        asset_class=asset_class,
        provider="pionex_public_futures",
        status="TRADING",
        intervals=("15M", "60M", "4H", "8H", "1D"),
        spread_bps=8.0,
        session_model_verified=session,
        corporate_action_policy=session,
    )


def _manual_candidate(
    *,
    plan_id: str = "integrated-long",
    side: str = "LONG",
    signal_time_ms: int = 0,
    stop_price: float = 98.0,
    target_price: float = 104.0,
) -> IntegratedCandidate:
    plan = DirectionalPlan(
        plan_id=plan_id,
        symbol="BTC_USDT_PERP",
        side=side,  # type: ignore[arg-type]
        signal_time_ms=signal_time_ms,
        stop_price=stop_price,
        target_price=target_price,
    )
    directional = DirectionalCandidate(
        plan=plan,
        score=85.0,
        eligible=True,
        reasons=("eligible_paper_challenger",),
        reference_price=100.0,
        features=(("adx14", 30.0),),
    )
    return IntegratedCandidate(
        market=_market(),
        directional=directional,
        regime="TREND_UP" if side == "LONG" else "TREND_DOWN",
        volatility_regime="NORMAL",
        sstate_bridge_mode="FORMAL_V0_1_DECISION_REQUIRED",
        formal_strategy_decision=None,
        research_context=ResearchContext(),
        stop_source="DIRECTIONAL_ATR",
        stop_distance_atr=1.5,
        eligible=True,
        reasons=("eligible_integrated_paper_candidate",),
    )


class IntegratedPaperStrategyCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = _config()

    def test_long_requires_both_formal_and_technical_gates(self) -> None:
        technical = _technical("LONG")
        candidates = build_integrated_candidates(
            market=_market(),
            opportunity=_opportunity(),
            technical=technical,
            advanced=_advanced("LONG"),
            higher=(technical, technical, technical, technical),
            config=self.config,
        )
        long = next(item for item in candidates if item.directional.plan.side == "LONG")
        self.assertTrue(long.eligible)
        self.assertIsNotNone(long.formal_strategy_decision)
        self.assertGreaterEqual(long.formal_strategy_decision.score, 80.0)  # type: ignore[union-attr]
        self.assertGreaterEqual(long.directional.score, 65.0)

    def test_long_sstate_probability_failure_remains_hard_gate(self) -> None:
        technical = _technical("LONG")
        candidates = build_integrated_candidates(
            market=_market(),
            opportunity=_opportunity(probability=0.59),
            technical=technical,
            advanced=_advanced("LONG"),
            higher=(technical, technical, technical, technical),
            config=self.config,
        )
        long = next(item for item in candidates if item.directional.plan.side == "LONG")
        self.assertFalse(long.eligible)
        self.assertIn("formal_strategy_probability_below_gate", long.reasons)

    def test_structural_stop_can_use_bollinger_mid_with_atr_bound(self) -> None:
        technical = _technical("LONG")
        technical.bollinger_mid = 96.0
        candidates = build_integrated_candidates(
            market=_market(),
            opportunity=_opportunity(),
            technical=technical,
            advanced=_advanced("LONG"),
            higher=(technical, technical, technical, technical),
            config=self.config,
        )
        long = next(item for item in candidates if item.directional.plan.side == "LONG")
        self.assertEqual(long.stop_source, "BOLLINGER_MID_BUFFERED_ATR_BOUNDED")
        self.assertEqual(long.stop_distance_atr, 2.5)
        self.assertEqual(long.directional.plan.stop_price, 97.0)

    def test_structural_stop_can_use_half_of_lower_bollinger_channel(self) -> None:
        technical = _technical("LONG")
        technical.bollinger_mid = 100.0
        technical.bollinger_lower = 96.0
        candidates = build_integrated_candidates(
            market=_market(),
            opportunity=_opportunity(),
            technical=technical,
            advanced=_advanced("LONG"),
            higher=(technical, technical, technical, technical),
            config=self.config,
        )
        long = next(item for item in candidates if item.directional.plan.side == "LONG")
        self.assertEqual(long.stop_source, "BOLLINGER_HALF_BAND_BUFFERED")
        self.assertAlmostEqual(long.directional.plan.stop_price, 97.8)
        self.assertAlmostEqual(long.stop_distance_atr, 2.1)

    def test_short_uses_context_only_bridge_not_long_setup_score(self) -> None:
        technical = _technical("SHORT")
        candidates = build_integrated_candidates(
            market=_market(),
            opportunity=_opportunity(good_features=False),
            technical=technical,
            advanced=_advanced("SHORT"),
            higher=(technical, technical, technical, technical),
            config=self.config,
        )
        short = next(item for item in candidates if item.directional.plan.side == "SHORT")
        self.assertTrue(short.eligible)
        self.assertEqual(short.sstate_bridge_mode, "CONTEXT_ONLY_RESEARCH")
        self.assertIsNone(short.formal_strategy_decision)

    def test_research_context_is_recorded_but_cannot_change_eligibility(self) -> None:
        technical = _technical("LONG")
        context = ResearchContext("CONTRADICTORY", 3, 1234)
        candidates = build_integrated_candidates(
            market=_market(),
            opportunity=_opportunity(),
            technical=technical,
            advanced=_advanced("LONG"),
            higher=(technical, technical, technical, technical),
            config=self.config,
            research_context=context,
        )
        long = next(item for item in candidates if item.directional.plan.side == "LONG")
        self.assertTrue(long.eligible)
        self.assertFalse(long.evidence()["researchContextChangesEligibility"])
        self.assertEqual(long.evidence()["researchContext"]["status"], "CONTRADICTORY")

    def test_tokenized_market_fails_closed_without_session_and_action_policy(self) -> None:
        technical = _technical("LONG")
        market = _market(asset_class="tokenized_stock_candidate", session=False)
        opportunity = _opportunity()
        opportunity = OpportunityInput(
            symbol=market.symbol,
            sstate=opportunity.sstate,
            setup=opportunity.setup,
            entry=opportunity.entry,
            reward_risk=opportunity.reward_risk,
            liquidity_ok=True,
            funding_ok=True,
        )
        candidates = build_integrated_candidates(
            market=market,
            opportunity=opportunity,
            technical=technical,
            advanced=_advanced("LONG"),
            higher=(technical, technical, technical, technical),
            config=self.config,
        )
        long = next(item for item in candidates if item.directional.plan.side == "LONG")
        self.assertFalse(long.eligible)
        self.assertIn("session_model_not_verified", long.reasons)
        self.assertIn("corporate_action_policy_missing", long.reasons)


class IntegratedPaperStrategyReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = _config()

    def test_partial_runner_and_target_are_executed(self) -> None:
        candles = (
            Candle(STEP, 100.0, 101.0, 99.0, 100.5, 10.0),
            Candle(2 * STEP, 100.5, 102.6, 100.4, 102.2, 10.0),
            Candle(3 * STEP, 102.2, 104.5, 102.0, 104.0, 10.0),
        )
        result = run_integrated_paper_replay(
            candidates=(_manual_candidate(),),
            candles_by_symbol={"BTC_USDT_PERP": candles},
            config=self.config,
        )
        trade = result["paperTrades"][0]
        self.assertEqual(result["metrics"]["trade_count"], 1)
        self.assertIsNotNone(trade["partial_exit_time_ms"])
        self.assertEqual(trade["partial_fraction"], 0.3)
        self.assertIn(trade["exit_reason"], {"runner_target", "target_after_partial_same_bar"})
        self.assertGreater(trade["net_pnl_usd"], 0.0)

    def test_hard_twelve_hour_time_exit_is_enforced(self) -> None:
        deadline = STEP + 720 * 60_000
        candles = (
            Candle(STEP, 100.0, 101.0, 99.0, 100.0, 10.0),
            Candle(deadline - STEP, 100.0, 101.0, 99.5, 100.5, 10.0),
            Candle(deadline, 100.5, 101.0, 100.0, 100.4, 10.0),
        )
        result = run_integrated_paper_replay(
            candidates=(_manual_candidate(),),
            candles_by_symbol={"BTC_USDT_PERP": candles},
            config=self.config,
        )
        trade = result["paperTrades"][0]
        self.assertEqual(trade["exit_reason"], "time_exit")
        self.assertEqual(trade["holding_minutes"], 720.0)

    def test_tight_stop_is_rejected_instead_of_silently_scaled(self) -> None:
        candles = (
            Candle(STEP, 100.0, 101.0, 99.95, 100.5, 10.0),
            Candle(2 * STEP, 100.5, 101.0, 100.0, 100.5, 10.0),
        )
        candidate = _manual_candidate(stop_price=99.9, target_price=103.0)
        result = run_integrated_paper_replay(
            candidates=(candidate,),
            candles_by_symbol={"BTC_USDT_PERP": candles},
            config=self.config,
        )
        self.assertEqual(result["metrics"]["trade_count"], 0)
        self.assertIn(
            [candidate.directional.plan.plan_id, "required_leverage_exceeds_cap"],
            result["rejectedPlans"],
        )
        self.assertEqual(
            result["riskDiagnostics"]["required_leverage_exceeds_cap_count"], 1
        )
        self.assertEqual(result["riskDiagnostics"]["leverage_rejection_fraction"], 1.0)

    def test_wider_stop_reduces_position_size_without_increasing_equity_risk(self) -> None:
        candles = (
            Candle(STEP, 100.0, 101.0, 99.0, 100.5, 10.0),
            Candle(2 * STEP, 100.5, 111.0, 99.0, 110.0, 10.0),
        )
        narrow = run_integrated_paper_replay(
            candidates=(
                _manual_candidate(plan_id="narrow", stop_price=96.0, target_price=110.0),
            ),
            candles_by_symbol={"BTC_USDT_PERP": candles},
            config=self.config,
        )["paperTrades"][0]
        wide = run_integrated_paper_replay(
            candidates=(
                _manual_candidate(plan_id="wide", stop_price=94.0, target_price=110.0),
            ),
            candles_by_symbol={"BTC_USDT_PERP": candles},
            config=self.config,
        )["paperTrades"][0]
        self.assertLess(wide["quantity"], narrow["quantity"])
        self.assertAlmostEqual(wide["risk_usd"], narrow["risk_usd"])
        self.assertEqual(wide["effective_risk_fraction"], 0.01)

    def test_portfolio_remains_single_position(self) -> None:
        candles = (
            Candle(STEP, 100.0, 101.0, 99.0, 100.5, 10.0),
            Candle(2 * STEP, 100.5, 101.0, 100.0, 100.5, 10.0),
            Candle(3 * STEP, 100.5, 104.5, 100.0, 104.0, 10.0),
        )
        first = _manual_candidate(plan_id="first")
        second = _manual_candidate(plan_id="second", signal_time_ms=STEP)
        result = run_integrated_paper_replay(
            candidates=(first, second),
            candles_by_symbol={"BTC_USDT_PERP": candles},
            config=self.config,
        )
        self.assertEqual(result["metrics"]["trade_count"], 1)
        self.assertIn(["second", "position_overlap"], result["rejectedPlans"])
        self.assertEqual(result["riskDiagnostics"]["maximum_concurrent_positions"], 1)

    def test_authority_remains_paper_only(self) -> None:
        authority = self.config["authority"]
        self.assertTrue(all(value is False for value in authority.values()))
        baseline = json.loads(
            (ROOT / "config" / "strategy_v0_1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(baseline["direction"], "LONG_ONLY")

    def test_invalid_ohlc_range_fails_closed(self) -> None:
        candles = (Candle(STEP, 100.0, 99.0, 101.0, 100.0, 10.0),)
        with self.assertRaisesRegex(ValueError, "invalid candle range"):
            run_integrated_paper_replay(
                candidates=(_manual_candidate(),),
                candles_by_symbol={"BTC_USDT_PERP": candles},
                config=self.config,
            )

    def test_prepared_receipt_hashes_and_authority_boundary(self) -> None:
        receipt = json.loads(
            (
                ROOT
                / "research"
                / "receipts"
                / "2026-08-26-integrated-paper-strategy-challenger-v0-2-1-structural-stop-amendment-prepared.json"
            ).read_text(encoding="utf-8")
        )
        for relative_path, expected_hash in receipt["sha256"].items():
            actual_hash = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(actual_hash, expected_hash)
        self.assertFalse(receipt["execution_boundary"]["workflow_created"])
        self.assertFalse(receipt["execution_boundary"]["replacement_holdout_accessed"])
        self.assertFalse(receipt["execution_boundary"]["live_trading_authorized"])


if __name__ == "__main__":
    unittest.main()
