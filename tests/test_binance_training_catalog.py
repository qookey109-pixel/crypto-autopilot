from __future__ import annotations

import unittest

from crypto_autopilot.binance_training_catalog import (
    classify_asset,
    parse_exchange_info,
)


def symbol(symbol: str, base: str, quote: str = "USDT", *, allowed: bool = True) -> dict:
    return {
        "symbol": symbol,
        "baseAsset": base,
        "quoteAsset": quote,
        "status": "TRADING",
        "isSpotTradingAllowed": allowed,
    }


class BinanceTrainingCatalogTests(unittest.TestCase):
    def test_filters_status_spot_permission_and_quote(self) -> None:
        payload = {
            "symbols": [
                symbol("BTCUSDT", "BTC"),
                symbol("TSLABUSDT", "TSLAB"),
                symbol("ETHUSDC", "ETH", "USDC"),
                {**symbol("OLDUSDT", "OLD"), "status": "BREAK"},
                symbol("NOUSDT", "NO", allowed=False),
                symbol("EURBTC", "EUR", "BTC"),
                symbol("币安人生USDC", "BNB", "USDC"),
            ]
        }
        markets = parse_exchange_info(payload)
        self.assertEqual([item.symbol for item in markets], ["ETHUSDC", "BTCUSDT", "TSLABUSDT"])
        self.assertEqual(markets[2].asset_class, "tokenized_stock_candidate")
        self.assertEqual(markets[2].classification_confidence, "heuristic")

    def test_all_quotes_and_stablecoin_classification(self) -> None:
        markets = parse_exchange_info(
            {"symbols": [symbol("USDTBTC", "USDT", "BTC"), symbol("EURBTC", "EUR", "BTC")]},
            all_quotes=True,
        )
        self.assertEqual(len(markets), 2)
        self.assertEqual({item.asset_class for item in markets}, {"stablecoin", "crypto"})
        self.assertEqual(classify_asset("USDT")[0], "stablecoin")

    def test_suffix_b_crypto_exception_is_not_stock(self) -> None:
        self.assertEqual(classify_asset("DGB")[0], "crypto")


if __name__ == "__main__":
    unittest.main()
