import unittest

from crypto_autopilot.features.regime import MarketRegimeSnapshot
from crypto_autopilot.opportunity_engine import (
    DailyOpportunityPolicy,
    rank_daily_opportunities,
)
from crypto_autopilot.technical import TechnicalSnapshot
from crypto_autopilot.universe import UniverseCandidate


def technical(
    *,
    close: float,
    ema20: float,
    ema50: float,
    ema200: float,
    slope_atr: float,
    macd_histogram: float,
    rsi14: float,
    bollinger_position: float,
    volume_ratio: float = 1.2,
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
        atr14_fraction=0.02,
        bollinger_mid=close,
        bollinger_upper=close * 1.05,
        bollinger_lower=close * 0.95,
        bollinger_bandwidth=0.10,
        bollinger_position=bollinger_position,
    )


def regime(*, available_at_ms: int = 1000, state: str = "MIXED") -> MarketRegimeSnapshot:
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


class DailyOpportunityEngineTests(unittest.TestCase):
    def test_ranks_stronger_multi_asset_candidate_first(self) -> None:
        universe = [
            UniverseCandidate("AAA_USDT_PERP", 5_000_000.0, 5.0, 120.0, 50_000),
            UniverseCandidate("BBB_USDT_PERP", 4_000_000.0, 8.0, 80.0, 40_000),
        ]
        snapshots = {
            "AAA_USDT_PERP": technical(
                close=120.0,
                ema20=115.0,
                ema50=110.0,
                ema200=100.0,
                slope_atr=0.4,
                macd_histogram=2.0,
                rsi14=62.0,
                bollinger_position=0.8,
            ),
            "BBB_USDT_PERP": technical(
                close=80.0,
                ema20=81.0,
                ema50=82.0,
                ema200=83.0,
                slope_atr=0.0,
                macd_histogram=0.0,
                rsi14=50.0,
                bollinger_position=0.5,
                volume_ratio=0.8,
            ),
        }

        report = rank_daily_opportunities(
            universe, snapshots, regime(), as_of_ms=1000
        )

        self.assertEqual(report.status, "CANDIDATES_READY")
        self.assertEqual(report.selected[0].symbol, "AAA_USDT_PERP")
        self.assertEqual(report.selected[0].bias, "LONG_BIAS")
        self.assertGreater(report.selected[0].attention_score, report.evaluated[1].attention_score)

    def test_direction_is_not_hard_coded_long_only(self) -> None:
        universe = [
            UniverseCandidate("AAA_USDT_PERP", 5_000_000.0, 5.0, 80.0, 50_000),
        ]
        snapshots = {
            "AAA_USDT_PERP": technical(
                close=80.0,
                ema20=85.0,
                ema50=90.0,
                ema200=100.0,
                slope_atr=-0.5,
                macd_histogram=-2.0,
                rsi14=35.0,
                bollinger_position=0.2,
            )
        }

        report = rank_daily_opportunities(
            universe, snapshots, regime(state="BROAD_RISK_OFF"), as_of_ms=1000
        )

        self.assertEqual(report.status, "CANDIDATES_READY")
        self.assertEqual(report.selected[0].bias, "SHORT_BIAS")

    def test_can_return_zero_candidates(self) -> None:
        universe = [
            UniverseCandidate("AAA_USDT_PERP", 1_000_000.0, 20.0, 100.0, 10_000),
        ]
        snapshots = {
            "AAA_USDT_PERP": technical(
                close=100.0,
                ema20=100.0,
                ema50=100.0,
                ema200=100.0,
                slope_atr=0.0,
                macd_histogram=0.0,
                rsi14=50.0,
                bollinger_position=0.5,
                volume_ratio=0.5,
            )
        }

        report = rank_daily_opportunities(
            universe,
            snapshots,
            regime(),
            as_of_ms=1000,
            policy=DailyOpportunityPolicy(minimum_attention_score=80.0),
        )

        self.assertEqual(report.status, "NO_CANDIDATE")
        self.assertEqual(report.selected, ())

    def test_future_technical_evidence_fails_closed(self) -> None:
        universe = [
            UniverseCandidate("AAA_USDT_PERP", 5_000_000.0, 5.0, 120.0, 50_000),
        ]
        snapshots = {
            "AAA_USDT_PERP": technical(
                close=120.0,
                ema20=115.0,
                ema50=110.0,
                ema200=100.0,
                slope_atr=0.4,
                macd_histogram=2.0,
                rsi14=62.0,
                bollinger_position=0.8,
                available_at_ms=1001,
            )
        }

        report = rank_daily_opportunities(
            universe, snapshots, regime(), as_of_ms=1000
        )

        self.assertEqual(report.status, "NO_CANDIDATE")
        self.assertFalse(report.evaluated[0].eligible)
        self.assertEqual(report.evaluated[0].reasons, ("technical_evidence_unavailable",))

    def test_regime_must_be_causally_available(self) -> None:
        report = rank_daily_opportunities(
            (),
            {},
            regime(available_at_ms=1001),
            as_of_ms=1000,
        )
        self.assertEqual(report.status, "REGIME_UNAVAILABLE")
        self.assertEqual(report.selected, ())

    def test_maximum_candidates_is_a_cap_not_a_forced_trade_count(self) -> None:
        universe = [
            UniverseCandidate(f"C{index}_USDT_PERP", 10_000_000.0 - index, 2.0, 100.0, 10_000)
            for index in range(8)
        ]
        snapshots = {
            item.symbol: technical(
                close=120.0,
                ema20=115.0,
                ema50=110.0,
                ema200=100.0,
                slope_atr=0.4,
                macd_histogram=2.0,
                rsi14=62.0,
                bollinger_position=0.8,
            )
            for item in universe
        }

        report = rank_daily_opportunities(
            universe,
            snapshots,
            regime(),
            as_of_ms=1000,
            policy=DailyOpportunityPolicy(maximum_candidates=3),
        )

        self.assertEqual(len(report.selected), 3)
        self.assertEqual(len(report.evaluated), 8)


if __name__ == "__main__":
    unittest.main()
