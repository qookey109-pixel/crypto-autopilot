from __future__ import annotations

import json
import unittest
from pathlib import Path


class BinanceTrainingCatalogConfigTests(unittest.TestCase):
    def test_config_is_internal_only_and_provider_separated(self) -> None:
        config = json.loads(Path("config/binance_internal_training_v0_2.json").read_text())
        self.assertEqual(config["provider"], "binance_spot")
        self.assertEqual(config["market_data_base_url"], "https://data-api.binance.vision")
        self.assertEqual(config["default_quotes"], ["USDT", "USDC"])
        self.assertFalse(config["website_projection_authorized"])
        for key in (
            "production_r2_access_authorized",
            "provider_splicing_authorized",
            "pionex_native_relabel_authorized",
            "source_switch_authorized",
            "holdout_access_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(config["authority"][key])


if __name__ == "__main__":
    unittest.main()
