import unittest

from crypto_autopilot.models import BookTicker, MarketTicker
from crypto_autopilot.universe import base_asset_from_symbol, rank_perpetual_universe


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

    def test_crypto_allowlist_blocks_non_crypto_instruments(self) -> None:
        active = ["BTC_USDT_PERP", "XAU_USDT_PERP", "SOXLX_USDT_PERP"]
        tickers = [
            MarketTicker(symbol, 10.0, 1.0, amount, 1)
            for symbol, amount in [
                ("BTC_USDT_PERP", 100.0),
                ("XAU_USDT_PERP", 10_000.0),
                ("SOXLX_USDT_PERP", 20_000.0),
            ]
        ]
        books = [BookTicker(symbol, 9.99, 1.0, 10.01, 1.0, 1) for symbol in active]
        ranked = rank_perpetual_universe(
            active,
            tickers,
            books,
            target_size=15,
            allowed_base_assets={"BTC", "ETH"},
        )
        self.assertEqual([item.symbol for item in ranked], ["BTC_USDT_PERP"])

    def test_base_asset_extraction_is_explicit(self) -> None:
        self.assertEqual(base_asset_from_symbol("BTC_USDT_PERP"), "BTC")
        self.assertIsNone(base_asset_from_symbol("BTC_USDC_PERP"))


if __name__ == "__main__":
    unittest.main()
