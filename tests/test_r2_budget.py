import unittest

from crypto_autopilot.storage.budget import R2Guardrails, R2Pricing, R2ProjectedUsage, evaluate_r2_budget


PRICING = R2Pricing(
    free_storage_gb_month=10.0,
    storage_usd_per_gb_month=0.015,
    free_class_a_requests_per_month=1_000_000,
    class_a_usd_per_million=4.5,
    free_class_b_requests_per_month=10_000_000,
    class_b_usd_per_million=0.36,
)

GUARDRAILS = R2Guardrails(
    storage_warn_gb_month=8.0,
    storage_block_gb_month=10.0,
    class_a_warn_requests_per_month=750_000,
    class_a_block_requests_per_month=1_000_000,
    class_b_warn_requests_per_month=7_500_000,
    class_b_block_requests_per_month=10_000_000,
)


class R2BudgetTests(unittest.TestCase):
    def test_planned_250_market_8_year_usage_passes(self) -> None:
        result = evaluate_r2_budget(
            R2ProjectedUsage(
                storage_gb_month=5.9117624762,
                class_a_requests_per_month=224_000,
                class_b_requests_per_month=140_000,
            ),
            PRICING,
            GUARDRAILS,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["estimated_monthly_cost_usd"]["total"], 0.0)

    def test_three_x_storage_stress_warns_but_remains_free(self) -> None:
        result = evaluate_r2_budget(
            R2ProjectedUsage(
                storage_gb_month=8.8676437143,
                class_a_requests_per_month=672_000,
                class_b_requests_per_month=420_000,
            ),
            PRICING,
            GUARDRAILS,
        )
        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["component_status"]["storage"], "WARN")
        self.assertEqual(result["estimated_monthly_cost_usd"]["total"], 0.0)

    def test_storage_above_free_envelope_blocks_and_rounds_up(self) -> None:
        result = evaluate_r2_budget(
            R2ProjectedUsage(
                storage_gb_month=10.1,
                class_a_requests_per_month=100,
                class_b_requests_per_month=100,
            ),
            PRICING,
            GUARDRAILS,
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["billable_after_free_tier_rounding"]["storage_gb_month"],
            1,
        )
        self.assertEqual(result["estimated_monthly_cost_usd"]["storage"], 0.015)

    def test_operation_overage_rounds_to_million_request_units(self) -> None:
        result = evaluate_r2_budget(
            R2ProjectedUsage(
                storage_gb_month=1.0,
                class_a_requests_per_month=1_000_001,
                class_b_requests_per_month=10_000_001,
            ),
            PRICING,
            GUARDRAILS,
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["estimated_monthly_cost_usd"]["class_a"], 4.5)
        self.assertEqual(result["estimated_monthly_cost_usd"]["class_b"], 0.36)


if __name__ == "__main__":
    unittest.main()
