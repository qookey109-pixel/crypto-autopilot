import unittest

from crypto_autopilot.models import EntryFeatures, OpportunityInput, SStateContext, SetupFeatures
from crypto_autopilot.strategy import evaluate_opportunity


GOOD_SETUP = SetupFeatures(True, True, True, True)
GOOD_ENTRY = EntryFeatures(True, True, True, True)


class StrategyTests(unittest.TestCase):
    def test_high_quality_s3_is_eligible(self) -> None:
        item = OpportunityInput(
            symbol="BTC_USDT_PERP",
            sstate=SStateContext("S3", 0.68, 120),
            setup=GOOD_SETUP,
            entry=GOOD_ENTRY,
            reward_risk=2.0,
            liquidity_ok=True,
            funding_ok=True,
        )
        decision = evaluate_opportunity(item)
        self.assertTrue(decision.eligible)
        self.assertGreaterEqual(decision.score, 80)

    def test_probability_gate_is_hard_gate(self) -> None:
        item = OpportunityInput(
            symbol="BTC_USDT_PERP",
            sstate=SStateContext("S3", 0.59, 500),
            setup=GOOD_SETUP,
            entry=GOOD_ENTRY,
            reward_risk=3.0,
            liquidity_ok=True,
            funding_ok=True,
        )
        decision = evaluate_opportunity(item)
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, "probability_below_gate")

    def test_unmodeled_state_is_rejected(self) -> None:
        item = OpportunityInput(
            symbol="BTC_USDT_PERP",
            sstate=SStateContext("S0", 0.80, 500),
            setup=GOOD_SETUP,
            entry=GOOD_ENTRY,
            reward_risk=3.0,
            liquidity_ok=True,
            funding_ok=True,
        )
        decision = evaluate_opportunity(item)
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, "state_not_allowed")


if __name__ == "__main__":
    unittest.main()
