from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from crypto_autopilot.backtest import FundingPoint
from crypto_autopilot.models import Candle
from crypto_autopilot.tokenized_equity_challenger_v0_1 import (
    TokenizedEquityCandidate,
    TokenizedEquityMarket,
    run_tokenized_equity_paper_replay,
    score_tokenized_equity_candidate,
)


ROOT = Path(__file__).resolve().parents[1]


def _candles() -> tuple[Candle, ...]:
    return (
        Candle(1_000, 100.0, 101.0, 99.0, 100.0, 10.0),
        Candle(2_000, 100.0, 101.0, 99.5, 100.5, 10.0),
        Candle(3_000, 100.5, 104.0, 100.0, 103.0, 10.0),
    )


class TokenizedEquityChallengerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(
            (ROOT / "config" / "tokenized_equity_challenger_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        self.market = TokenizedEquityMarket(
            symbol="TSLA_USDT_PERP",
            asset_class="tokenized_stock_candidate",
            status="TRADING",
            provider="pionex_public_futures",
            intervals=("15M", "60M", "4H", "8H", "1D"),
            session_model_verified=True,
            corporate_action_policy=True,
            spread_bps=12.0,
        )

    def _candidate(self, *, eligible: bool = True) -> TokenizedEquityCandidate:
        core = type(
            "CoreCandidate",
            (),
            {
                "plan_id": "paper-tsla",
                "symbol": self.market.symbol,
                "signal_time_ms": 1_000,
                "stop_price": 98.0,
                "target_price": 103.0,
                "score": 82.0,
                "features": (("adx14", 25.0),),
            },
        )()
        # The candidate property only needs the core fields above in this
        # deterministic replay fixture; the plan is validated by the engine.
        return TokenizedEquityCandidate(
            self.market,
            core,  # type: ignore[arg-type]
            eligible,
            ("eligible_paper_candidate",) if eligible else ("session_model_not_verified",),
        )

    def test_valid_tokenized_candidate_can_replay_with_crypto_geometry(self) -> None:
        result = run_tokenized_equity_paper_replay(
            candidates=(self._candidate(),),
            candles_by_symbol={self.market.symbol: _candles()},
            funding_points=(FundingPoint(self.market.symbol, 2_000, 0.001),),
            config=self.config,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["assetClass"], "tokenized_stock_candidate")
        self.assertEqual(result["eligibleCandidateCount"], 1)
        self.assertEqual(result["metrics"]["trade_count"], 1)
        self.assertTrue(result["interpretation"]["asset_class_isolated"])

    def test_valid_market_uses_the_configured_crypto_scorer(self) -> None:
        technical = SimpleNamespace(
            bar_time_ms=1_000,
            ready_v0_2=True,
            ema20=101.0,
            ema50=100.0,
            ema200=99.0,
            ema20_slope=0.2,
            close=102.0,
            atr14=1.0,
            rsi14=60.0,
            macd_histogram=0.3,
        )
        advanced = SimpleNamespace(
            ready=True,
            adx14=25.0,
            plus_di14=30.0,
            minus_di14=15.0,
            vwap_distance_fraction=0.02,
            volume_zscore20=1.0,
            donchian_position20=0.9,
            atr_percentile100=0.5,
            bollinger_bandwidth_percentile100=0.5,
            realized_volatility20=0.02,
            parkinson_volatility20=0.02,
            volatility_of_volatility20=0.01,
            kaufman_efficiency_ratio10=0.6,
            choppiness_index14=35.0,
            volatility_adjusted_momentum20=0.4,
        )
        higher = (technical, technical, technical, technical)
        candidate = score_tokenized_equity_candidate(
            market=self.market,
            technical=technical,
            advanced=advanced,
            higher=higher,
            config=self.config,
        )
        self.assertIsNotNone(candidate.core_candidate)
        self.assertTrue(candidate.eligible)
        self.assertEqual(candidate.market.asset_class, "tokenized_stock_candidate")

    def test_wrong_asset_class_is_rejected_before_replay(self) -> None:
        market = TokenizedEquityMarket(
            symbol="BTC_USDT_PERP",
            asset_class="crypto",
            status="TRADING",
            provider="pionex_public_futures",
            intervals=("15M", "60M", "4H", "8H", "1D"),
            session_model_verified=True,
            corporate_action_policy=True,
            spread_bps=5.0,
        )
        self.assertEqual(market.asset_class, "crypto")
        candidate = TokenizedEquityCandidate(
            market, None, False, ("asset_class_not_tokenized_stock_candidate",)
        )
        result = run_tokenized_equity_paper_replay(
            candidates=(candidate,),
            candles_by_symbol={market.symbol: _candles()},
            config=self.config,
        )
        self.assertEqual(result["eligibleCandidateCount"], 0)
        self.assertIn("asset_class_not_tokenized_stock_candidate", result["rejectedCandidates"][0])

    def test_missing_metadata_gate_is_rejected(self) -> None:
        candidate = TokenizedEquityCandidate(
            TokenizedEquityMarket(
                symbol=self.market.symbol,
                asset_class=self.market.asset_class,
                status=self.market.status,
                provider=self.market.provider,
                intervals=self.market.intervals,
                session_model_verified=False,
                corporate_action_policy=False,
                spread_bps=12.0,
            ),
            None,
            False,
            ("session_model_not_verified", "corporate_action_policy_missing"),
        )
        result = run_tokenized_equity_paper_replay(
            candidates=(candidate,),
            candles_by_symbol={self.market.symbol: _candles()},
            config=self.config,
        )
        self.assertEqual(result["metrics"]["trade_count"], 0)
        self.assertEqual(result["authority"]["live_trading_authorized"], False)

    def test_config_keeps_formal_crypto_universe_and_authority_separate(self) -> None:
        crypto_config = json.loads(
            (ROOT / "config" / "crypto_universe_v0_1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.config["status"], "PREPARED_LOCAL_REPLAY_ONLY")
        self.assertTrue(self.config["interpretation"]["asset_class_isolated"])
        self.assertTrue(self.config["authority"]["live_trading_authorized"] is False)
        self.assertEqual(crypto_config["policy"]["selected_universe_target"], 15)
        self.assertNotIn("TSLA", crypto_config["base_assets"])


if __name__ == "__main__":
    unittest.main()
