from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BinanceSpotHistoryConfigTests(unittest.TestCase):
    def test_local_research_scope_is_provider_separated_and_non_trading(self) -> None:
        config = json.loads(
            (ROOT / "config" / "binance_spot_history_v0_1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["provider"], "binance_spot")
        self.assertEqual(config["market_data_base_url"], "https://data-api.binance.vision")
        self.assertEqual(config["start_utc"], "2020-01-01T00:00:00Z")
        self.assertEqual(config["interval"], "1d")
        self.assertEqual(len(config["symbols"]), 15)
        authority = config["authority"]
        self.assertTrue(authority["local_public_market_reads_authorized"])
        self.assertTrue(authority["local_artifact_write_authorized"])
        for key in (
            "production_r2_access_authorized",
            "provider_splicing_authorized",
            "pionex_native_relabel_authorized",
            "source_switch_authorized",
            "holdout_access_authorized",
            "trade_kline_w1_materialization_authorized",
            "formal_trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(authority[key], key)

    def test_local_pass_receipt_preserves_non_production_boundary(self) -> None:
        receipt = json.loads(
            (
                ROOT
                / "research"
                / "receipts"
                / "2026-08-22-binance-spot-history-v0-1-local-pass.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["provider"], "binance_spot")
        self.assertEqual(receipt["available_symbol_count"], 14)
        self.assertEqual(receipt["no_data_symbols"], ["HYPEUSDT"])
        self.assertEqual(receipt["row_count"], 31402)
        self.assertTrue(receipt["validation"]["available_series_audit_ok"])
        for key, value in receipt["authority_boundary"].items():
            self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
