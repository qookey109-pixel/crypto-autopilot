from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.pionex_asset_classification_verifier_v0_1 import (
    AssetClassificationRejected,
    validate_config,
    verify_selected_market_classification,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_asset_classification_verifier_v0_1.json"
ALTERNATIVE = ROOT / "config/pionex_alternative_assets_v0_1.json"


def universe(*markets: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "pionex-research-universe-run-report-v0.1",
        "status": "PASS",
        "provider": "pionex_public_futures",
        "selected_market_count": len(markets),
        "markets": list(markets),
    }


def market(symbol: str, base: str, asset_class: str = "crypto") -> dict[str, object]:
    return {
        "symbol": symbol,
        "base_asset": base,
        "asset_class": asset_class,
    }


def coins(*rows: dict[str, object]) -> bytes:
    return (json.dumps(list(rows), sort_keys=True) + "\n").encode()


def coin(
    coin_id: str,
    symbol: str,
    *,
    active: bool = True,
    coin_type: str = "coin",
) -> dict[str, object]:
    return {
        "id": coin_id,
        "name": coin_id,
        "symbol": symbol,
        "rank": 1 if active else 0,
        "is_new": False,
        "is_active": active,
        "type": coin_type,
    }


class PionexAssetClassificationVerifierV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.alternative_bytes = ALTERNATIVE.read_bytes()

    def verify(self, report: dict[str, object], payload: bytes) -> dict[str, object]:
        return verify_selected_market_classification(
            self.config,
            alternative_registry_bytes=self.alternative_bytes,
            universe_report=report,
            coinpaprika_payload=payload,
        )

    def test_config_is_prepared_only_and_grants_no_execution_authority(self) -> None:
        alternative_map = validate_config(
            self.config, alternative_registry_bytes=self.alternative_bytes
        )
        self.assertEqual(alternative_map["AAPLX"], "us_equity_token")
        self.assertEqual(self.config["status"], "PREPARED_NOT_EXECUTION_AUTHORITY")
        authority = self.config["authority"]
        self.assertTrue(authority["fixture_validation"])
        self.assertTrue(
            all(value is False for key, value in authority.items() if key != "fixture_validation")
        )
        self.assertFalse(self.config["prepared_execution_shape"]["workflow_included_by_this_stage"])

    def test_unique_active_crypto_and_alternative_registry_both_verify(self) -> None:
        report = universe(
            market("BTC_USDT_PERP", "BTC"),
            market("AAPLX_USDT_PERP", "AAPLX", "us_equity_token"),
        )
        result = self.verify(
            report,
            coins(
                coin("btc-bitcoin", "BTC"),
                # Even a CoinPaprika collision cannot override the Pionex alternative registry.
                coin("aaplx-fake-crypto", "AAPLX", coin_type="token"),
            ),
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["all_selected_markets_verified"])
        self.assertEqual(result["verified_crypto_count"], 1)
        self.assertEqual(result["verified_alternative_count"], 1)
        self.assertEqual(result["unresolved_count"], 0)
        self.assertFalse(result["full_simulation_readiness_cleared_by_this_result"])
        self.assertFalse(result["universe_fallback_crypto_labels_used_as_evidence"])
        rows = {row["symbol"]: row for row in result["classifications"]}
        self.assertEqual(rows["BTC_USDT_PERP"]["state"], "VERIFIED_CRYPTO")
        self.assertEqual(rows["BTC_USDT_PERP"]["coinpaprika_id"], "btc-bitcoin")
        self.assertEqual(rows["AAPLX_USDT_PERP"]["state"], "VERIFIED_ALTERNATIVE")
        self.assertEqual(
            rows["AAPLX_USDT_PERP"]["evidence"], "PIONEX_ALTERNATIVE_REGISTRY"
        )

    def test_ambiguous_active_crypto_symbol_remains_unresolved(self) -> None:
        result = self.verify(
            universe(market("ABC_USDT_PERP", "ABC")),
            coins(
                coin("abc-first", "ABC"),
                coin("abc-second", "ABC", coin_type="token"),
            ),
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["all_selected_markets_verified"])
        self.assertEqual(result["unresolved_symbols"], ["ABC_USDT_PERP"])
        row = result["classifications"][0]
        self.assertEqual(row["reason"], "AMBIGUOUS_ACTIVE_COINPAPRIKA_SYMBOL")
        self.assertEqual(row["candidate_ids"], ["abc-first", "abc-second"])

    def test_inactive_coinpaprika_entry_is_not_classification_evidence(self) -> None:
        result = self.verify(
            universe(market("OLD_USDT_PERP", "OLD")),
            coins(coin("old-inactive", "OLD", active=False)),
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["classifications"][0]["reason"],
            "NO_ACTIVE_COINPAPRIKA_SYMBOL_MATCH",
        )

    def test_universe_fallback_crypto_label_never_clears_missing_external_evidence(self) -> None:
        result = self.verify(
            universe(market("MISSING_USDT_PERP", "MISSING", "crypto")),
            coins(coin("btc-bitcoin", "BTC")),
        )
        row = result["classifications"][0]
        self.assertEqual(row["universe_fallback_asset_class"], "crypto")
        self.assertFalse(row["universe_fallback_used_as_evidence"])
        self.assertEqual(row["state"], "UNRESOLVED")
        self.assertFalse(result["all_selected_markets_verified"])

    def test_unknown_coinpaprika_type_is_rejected_instead_of_silently_accepted(self) -> None:
        with self.assertRaisesRegex(AssetClassificationRejected, "type invalid"):
            self.verify(
                universe(market("BTC_USDT_PERP", "BTC")),
                coins(coin("btc-bitcoin", "BTC", coin_type="equity")),
            )

    def test_safety_boundary_is_fully_closed(self) -> None:
        result = self.verify(
            universe(market("BTC_USDT_PERP", "BTC")),
            coins(coin("btc-bitcoin", "BTC")),
        )
        self.assertTrue(result["safety_boundary"])
        self.assertTrue(all(value is False for value in result["safety_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
