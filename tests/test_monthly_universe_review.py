from __future__ import annotations

import unittest

from crypto_autopilot.monthly_universe_review import (
    build_monthly_universe_objects,
    build_monthly_universe_review,
)


def market(symbol: str, asset_class: str = "crypto") -> dict:
    return {
        "symbol": symbol,
        "base_asset": symbol.removesuffix("USDT"),
        "quote_asset": "USDT",
        "asset_class": asset_class,
        "classification_method": "default_crypto"
        if asset_class == "crypto"
        else "trailing_B_heuristic",
        "classification_confidence": "default"
        if asset_class == "crypto"
        else "heuristic",
    }


class MonthlyUniverseReviewTests(unittest.TestCase):
    def test_changes_are_reported_without_claiming_delisting_or_membership(self) -> None:
        previous = build_monthly_universe_review(
            {"markets": [market("OLDUSDT"), market("TSLABUSDT", "tokenized_stock_candidate")]},
            previous_review=None,
            generated_at_utc="2026-07-01T00:00:00Z",
        )
        current = build_monthly_universe_review(
            {"markets": [market("NEWUSDT"), market("TSLABUSDT", "crypto")]},
            previous_review=previous,
            generated_at_utc="2026-08-01T00:00:00Z",
        )
        self.assertEqual(current["added_since_previous_monthly_review"], ["NEWUSDT"])
        self.assertEqual(current["absent_from_current_active_catalog"], ["OLDUSDT"])
        self.assertEqual(len(current["classification_changes"]), 1)
        survivorship = current["survivorship_bias_review"]
        self.assertEqual(survivorship["status"], "REVIEW_REQUIRED")
        self.assertFalse(survivorship["absence_from_current_catalog_is_delisting_proof"])
        self.assertFalse(current["authority"]["historical_universe_membership_authorized"])

    def test_latest_pointer_is_last(self) -> None:
        config = {
            "monthly_universe_review": {
                "namespace": "research/binance/universe/v0.4",
                "latest_pointer_key": "research/binance/universe/v0.4/latest.json",
            }
        }
        objects = build_monthly_universe_objects(
            config=config,
            run_id="monthly-1",
            catalog=b"{}\n",
            review=b"{}\n",
            generated_at_utc="2026-08-01T00:00:00Z",
        )
        self.assertEqual([item.role for item in objects], [
            "monthly_catalog",
            "monthly_universe_review",
            "latest_pointer",
        ])
        self.assertFalse(objects[-1].immutable)


if __name__ == "__main__":
    unittest.main()
