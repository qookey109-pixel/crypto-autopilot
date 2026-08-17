import unittest

from crypto_autopilot.models import BookTicker, MarketTicker
from crypto_autopilot.universe import rank_perpetual_universe


class UniverseTests(unittest.TestCase):
    def test_ranking_uses_turnover_then_spread(self) -> None:
        active = ["AAA_USDT_PERP", "BBB_USDT_PERP", "CCC_USDT_PERP", "AAA_USDT_PERP"]
        tickers = [
            MarketTicker("AAA_USDT_PERP", 10.0, 100.0, 1_000.0, 10),
            MarketTicker("BBB_USDT_PERP", 20.0, 100.0, 3_000.0, 20),
            MarketTicker("CCC_USDT_PERP", 30.0, 100.0, 2_000.0, 30),
        ]
        books = [
            BookTicker("AAA_USDT_PERP", 9.99, 1.0, 10.01, 1.0, 1),
            BookTicker("BBB_USDT_PERP", 19.99, 1.0, 20.01, 1.0, 1),
            BookTicker("CCC_USDT_PERP", 29.99, 1.0, 30.01, 1.0, 1),
        ]
        ranked = rank_perpetual_universe(active, tickers, books, target_size=2)
        self.assertEqual([item.symbol for item in ranked], ["BBB_USDT_PERP", "CCC_USDT_PERP"])

    def test_filters_non_usdt_and_wide_spreads(self) -> None:
        active = ["AAA_USDT_PERP", "BBB_USDT_PERP", "CCC_USDC_PERP"]
        tickers = [
            MarketTicker("AAA_USDT_PERP", 10.0, 1.0, 100.0, 1),
            MarketTicker("BBB_USDT_PERP", 10.0, 1.0, 200.0, 1),
            MarketTicker("CCC_USDC_PERP", 10.0, 1.0, 500.0, 1),
        ]
        books = [
            BookTicker("AAA_USDT_PERP", 9.99, 1.0, 10.01, 1.0, 1),
            BookTicker("BBB_USDT_PERP", 9.0, 1.0, 11.0, 1.0, 1),
            BookTicker("CCC_USDC_PERP", 9.99, 1.0, 10.01, 1.0, 1),
        ]
        ranked = rank_perpetual_universe(active, tickers, books, target_size=15, max_spread_bps=30)
        self.assertEqual([item.symbol for item in ranked], ["AAA_USDT_PERP"])


if __name__ == "__main__":
    unittest.main()
