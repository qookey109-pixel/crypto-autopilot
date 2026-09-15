from __future__ import annotations

import copy
import unittest

from crypto_autopilot.research.context import summarize_context
from crypto_autopilot.research.tradingagents_challenger import (
    TradingAgentsChallengerError,
    ingest_tradingagents_candidate,
)


def candidate_payload() -> dict[str, object]:
    return {
        "schema": "tradingagents-research-candidate-v0.1",
        "run_id": "ta-btc-20260915-001",
        "upstream": {
            "repository": "https://github.com/TauricResearch/TradingAgents",
            "version": "0.4.0",
            "commit": "a" * 40,
        },
        "symbol": "BTC_USDT_PERP",
        "upstream_ticker": "BTC-USD",
        "data_provider": "yfinance",
        "analysis_date": "2026-09-15",
        "decision_at_ms": 2_000,
        "data_cutoff_ms": 1_900,
        "rating": "Overweight",
        "point_in_time_verified": True,
        "reports": {
            "market_report": "Market evidence",
            "bull_case": "Bull evidence",
            "bear_case": "Bear evidence",
            "investment_plan": "Research proposal only",
            "risk_report": "Risk evidence",
            "final_trade_decision": "Five-tier rating",
        },
        "evidence_urls": [
            "https://github.com/TauricResearch/TradingAgents",
            "https://example.test/research/ta-btc-20260915-001",
        ],
        "authority": {
            "holdout_accessed": False,
            "source_switch_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


class TradingAgentsChallengerTests(unittest.TestCase):
    def test_valid_candidate_becomes_descriptive_context_only(self) -> None:
        item = ingest_tradingagents_candidate(
            candidate_payload(),
            as_of_ms=2_100,
            allowed_symbols=("BTC_USDT_PERP",),
            expected_data_provider="yfinance",
        )
        evidence = item.evidence()
        self.assertEqual(evidence["rating"], "OVERWEIGHT")
        self.assertEqual(evidence["rating_ordinal"], 1.0)
        self.assertEqual(evidence["report_count"], 6)
        self.assertNotIn("reports", evidence)
        self.assertFalse(evidence["direct_trade_trigger_authorized"])
        self.assertFalse(evidence["live_trading_authorized"])

        summary = summarize_context([item.context_observation()], as_of_ms=2_100)
        self.assertEqual(summary["status"], "READY")
        self.assertIsNone(summary["composite_score"])
        self.assertFalse(summary["trade_plan_authorized"])

    def test_future_data_provider_and_universe_mismatches_fail_closed(self) -> None:
        future = candidate_payload()
        future["decision_at_ms"] = 2_101
        with self.assertRaisesRegex(TradingAgentsChallengerError, "future"):
            ingest_tradingagents_candidate(future, as_of_ms=2_100)

        with self.assertRaisesRegex(TradingAgentsChallengerError, "allowed research universe"):
            ingest_tradingagents_candidate(
                candidate_payload(), as_of_ms=2_100, allowed_symbols=("ETH_USDT_PERP",)
            )
        with self.assertRaisesRegex(TradingAgentsChallengerError, "expected lineage"):
            ingest_tradingagents_candidate(
                candidate_payload(), as_of_ms=2_100, expected_data_provider="pionex"
            )

    def test_missing_point_in_time_or_protected_authority_fails_closed(self) -> None:
        no_pit = candidate_payload()
        no_pit["point_in_time_verified"] = False
        with self.assertRaisesRegex(TradingAgentsChallengerError, "point_in_time"):
            ingest_tradingagents_candidate(no_pit, as_of_ms=2_100)

        live = candidate_payload()
        live["authority"]["live_trading_authorized"] = True  # type: ignore[index]
        with self.assertRaisesRegex(TradingAgentsChallengerError, "explicitly false"):
            ingest_tradingagents_candidate(live, as_of_ms=2_100)

        leaked = candidate_payload()
        leaked["analysis_date"] = "1970-01-01"
        leaked["data_cutoff_ms"] = 86_400_000
        leaked["decision_at_ms"] = 90_000_000
        with self.assertRaisesRegex(TradingAgentsChallengerError, "analysis date"):
            ingest_tradingagents_candidate(leaked, as_of_ms=100_000_000)

    def test_secret_like_fields_and_mutated_run_identity_are_rejected_or_distinct(self) -> None:
        secret = candidate_payload()
        secret["api_key"] = "must-not-enter-evidence"
        with self.assertRaisesRegex(ValueError, "secret-like field"):
            ingest_tradingagents_candidate(secret, as_of_ms=2_100)

        order = candidate_payload()
        order["order_id"] = "external-order-must-not-enter"
        with self.assertRaisesRegex(TradingAgentsChallengerError, "unexpected top-level"):
            ingest_tradingagents_candidate(order, as_of_ms=2_100)

        first = ingest_tradingagents_candidate(candidate_payload(), as_of_ms=2_100)
        changed = copy.deepcopy(candidate_payload())
        changed["reports"]["bear_case"] = "Changed bear evidence"  # type: ignore[index]
        second = ingest_tradingagents_candidate(changed, as_of_ms=2_100)
        self.assertNotEqual(first.payload_sha256, second.payload_sha256)
        self.assertNotEqual(dict(first.report_sha256), dict(second.report_sha256))


if __name__ == "__main__":
    unittest.main()
