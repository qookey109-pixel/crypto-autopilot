import unittest

from crypto_autopilot.features.regime import MarketRegimeSnapshot
from crypto_autopilot.features.structure import MarketStructureSnapshot
from crypto_autopilot.opportunity_engine import DailyOpportunityDecision
from crypto_autopilot.strategy_router import route_strategy_families
from crypto_autopilot.technical import TechnicalSnapshot


def opportunity(
    *,
    profile: str = "DIRECTIONAL",
    bias: str = "LONG_BIAS",
    eligible: bool = True,
) -> DailyOpportunityDecision:
    return DailyOpportunityDecision(
        symbol="AAA_USDT_PERP",
        eligible=eligible,
        attention_score=90.0 if eligible else 40.0,
        bias=bias,
        liquidity_score=20.0,
        directional_score=70.0 if profile == "DIRECTIONAL" else 20.0,
        range_extremity_score=75.0 if profile == "RANGE_EXTREMITY" else 0.0,
        attention_profile=profile,
        regime_state="MIXED",
        reasons=("fixture",),
    )


def technical(
    *,
    close: float = 120.0,
    ema20: float = 115.0,
    ema50: float = 110.0,
    ema200: float = 100.0,
    slope_atr: float = 0.4,
    macd_histogram: float = 2.0,
    rsi14: float = 65.0,
    bollinger_position: float = 0.8,
    volume_ratio: float = 1.3,
    atr14_fraction: float = 0.02,
    available_at_ms: int = 1000,
) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        bar_time_ms=0,
        available_at_ms=available_at_ms,
        close=close,
        volume=100.0,
        ema20=ema20,
        ema50=ema50,
        ema20_slope=1.0 if slope_atr >= 0 else -1.0,
        atr14=2.0,
        volume_sma20=80.0,
        volume_ratio=volume_ratio,
        previous_high=close - 1.0,
        extension_from_ema20_atr=0.5,
        ema200=ema200,
        ema20_ema50_distance_fraction=(ema20 - ema50) / close,
        ema50_ema200_distance_fraction=(ema50 - ema200) / close,
        ema20_slope_atr=slope_atr,
        rsi14=rsi14,
        macd=1.0 if macd_histogram >= 0 else -1.0,
        macd_signal=0.5 if macd_histogram >= 0 else -0.5,
        macd_histogram=macd_histogram,
        atr14_fraction=atr14_fraction,
        bollinger_mid=close,
        bollinger_upper=close * 1.05,
        bollinger_lower=close * 0.95,
        bollinger_bandwidth=0.10,
        bollinger_position=bollinger_position,
    )


def structure(
    *,
    state: str = "UP",
    breakout: bool = False,
    breakdown: bool = False,
    available_at_ms: int = 1000,
) -> MarketStructureSnapshot:
    return MarketStructureSnapshot(
        bar_time_ms=0,
        available_at_ms=available_at_ms,
        rolling_previous_high=110.0,
        rolling_previous_low=90.0,
        breakout_above_previous_range=breakout,
        breakdown_below_previous_range=breakdown,
        distance_to_previous_high_atr=1.0,
        distance_to_previous_low_atr=10.0,
        confirmed_swing_high=False,
        confirmed_swing_low=False,
        most_recent_confirmed_swing_high=108.0,
        most_recent_confirmed_swing_low=92.0,
        market_structure_state=state,
    )


def regime(*, state: str = "ALT_EXPANSION", available_at_ms: int = 1000) -> MarketRegimeSnapshot:
    return MarketRegimeSnapshot(
        bar_time_ms=0,
        available_at_ms=available_at_ms,
        btc_return=0.01,
        total3_return=0.02,
        eth_btc_return=0.01,
        btc_dominance_delta_pct_points=-0.2,
        alt_breadth_above_ema20=0.6,
        alt_breadth_positive_momentum=0.6,
        alt_expansion_votes=4,
        btc_concentration_votes=1,
        broad_risk_off_votes=0,
        state=state,
    )


class StrategyRouterV01Tests(unittest.TestCase):
    def test_one_candidate_can_match_multiple_directional_families(self) -> None:
        decision = route_strategy_families(
            opportunity(),
            technical(atr14_fraction=0.04),
            regime(),
            structure(state="UP"),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "ROUTES_READY")
        self.assertEqual(
            tuple(match.family for match in decision.matches),
            ("TREND_FOLLOWING", "MOMENTUM", "HIGH_VOLATILITY_TREND"),
        )
        self.assertTrue(all(match.direction == "LONG" for match in decision.matches))

    def test_breakout_can_coexist_with_trend_and_momentum(self) -> None:
        decision = route_strategy_families(
            opportunity(),
            technical(),
            regime(),
            structure(state="UP", breakout=True),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "ROUTES_READY")
        self.assertEqual(
            tuple(match.family for match in decision.matches),
            ("TREND_FOLLOWING", "BREAKOUT", "MOMENTUM"),
        )

    def test_range_extremity_can_route_contrarian_to_descriptive_bias(self) -> None:
        decision = route_strategy_families(
            opportunity(profile="RANGE_EXTREMITY", bias="SHORT_BIAS"),
            technical(
                close=100.0,
                ema20=100.0,
                ema50=100.0,
                ema200=100.0,
                slope_atr=0.0,
                macd_histogram=0.0,
                rsi14=30.0,
                bollinger_position=0.10,
                volume_ratio=1.2,
                atr14_fraction=0.01,
            ),
            regime(state="MIXED"),
            structure(state="RANGE"),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "ROUTES_READY")
        self.assertEqual(
            tuple((match.family, match.direction) for match in decision.matches),
            (("MEAN_REVERSION", "LONG"), ("LOW_VOLATILITY_RANGE", "LONG")),
        )

    def test_no_compatible_family_returns_no_trade(self) -> None:
        decision = route_strategy_families(
            opportunity(profile="RANGE_EXTREMITY", bias="NEUTRAL"),
            technical(
                close=100.0,
                ema20=100.0,
                ema50=100.0,
                ema200=100.0,
                slope_atr=0.0,
                macd_histogram=0.0,
                rsi14=50.0,
                bollinger_position=0.50,
                volume_ratio=0.8,
                atr14_fraction=0.02,
            ),
            regime(state="MIXED"),
            structure(state="RANGE"),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "NO_TRADE")
        self.assertEqual(decision.matches, ())
        self.assertEqual(decision.reasons, ("no_strategy_family_matched",))

    def test_future_structure_cannot_create_a_breakout_route(self) -> None:
        decision = route_strategy_families(
            opportunity(),
            technical(rsi14=55.0, volume_ratio=1.0, slope_atr=0.05),
            regime(),
            structure(state="UP", breakout=True, available_at_ms=1001),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "NO_TRADE")
        self.assertEqual(decision.matches, ())

    def test_macro_conflict_fails_closed_for_directional_long_routes(self) -> None:
        decision = route_strategy_families(
            opportunity(),
            technical(atr14_fraction=0.04),
            regime(state="BROAD_RISK_OFF"),
            structure(state="UP", breakout=True),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "NO_TRADE")
        self.assertEqual(decision.matches, ())

    def test_future_technical_evidence_fails_closed(self) -> None:
        decision = route_strategy_families(
            opportunity(),
            technical(available_at_ms=1001),
            regime(),
            structure(),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "NO_TRADE")
        self.assertEqual(decision.reasons, ("technical_evidence_unavailable",))

    def test_ineligible_daily_candidate_is_not_routed(self) -> None:
        decision = route_strategy_families(
            opportunity(eligible=False),
            technical(),
            regime(),
            structure(),
            as_of_ms=1000,
        )

        self.assertEqual(decision.status, "NO_TRADE")
        self.assertEqual(decision.reasons, ("candidate_not_eligible",))


if __name__ == "__main__":
    unittest.main()
