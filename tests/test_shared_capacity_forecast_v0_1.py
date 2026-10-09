from __future__ import annotations

import unittest
from dataclasses import replace

from crypto_autopilot.paper.shared_capacity_forecast_v0_1 import (
    MeterAttemptDemand,
    SlotDemand,
    WriterDemand,
    forecast_shared_budget,
)


class SharedCapacityForecastV01Tests(unittest.TestCase):
    def slot(self) -> SlotDemand:
        return SlotDemand(
            provider_requests=1,
            r2_class_a=2,
            r2_class_b=1,
            r2_new_bytes=128,
            d1_queries=2,
            d1_rows_read=3,
            d1_rows_written=7,
            d1_storage_growth_bytes=100,
        )

    def writers(self) -> list[WriterDemand]:
        return [
            WriterDemand(
                writer_id="crypto:paper",
                successful_slots_per_day=2,
                replay_attempts_per_day=1,
                rejected_attempts_per_day=1,
                per_success_slot=self.slot(),
            ),
            WriterDemand(
                writer_id="other:writer",
                successful_slots_per_day=1,
                replay_attempts_per_day=0,
                rejected_attempts_per_day=0,
                per_success_slot=self.slot(),
            ),
        ]

    def meter(self) -> MeterAttemptDemand:
        return MeterAttemptDemand(
            control_d1_queries=1,
            control_d1_rows_read=2,
            control_d1_rows_written=1,
            control_d1_storage_growth_bytes=64,
            readback_d1_rows_read_per_statement=2,
        )

    def caps(self) -> dict:
        return {
            "daily": {
                "reservations": 3,
                "provider_requests": 3,
                "r2_class_a": 6,
                "r2_class_b": 3,
                "r2_new_bytes": 384,
                "d1_queries": 17,
                "d1_rows_read": 31,
                "d1_rows_written": 28,
                "d1_storage_growth_bytes": 748,
            },
            "rolling_31_days": {
                "r2_class_a": 186,
                "r2_class_b": 93,
                "r2_new_bytes": 11904,
            },
        }

    def test_two_writer_forecast_charges_failure_replay_and_controller(self) -> None:
        result = forecast_shared_budget(
            writers=self.writers(),
            query_attempt_cost=self.meter(),
            hypothetical_caps=self.caps(),
        )
        self.assertEqual(result["status"], "SCENARIO_WITHIN_INPUT_CAPS_NOT_AUTHORIZED")
        self.assertEqual(result["writer_ids"], ["crypto:paper", "other:writer"])
        self.assertEqual(result["daily_successful_reservations"], 3)
        self.assertEqual(result["daily_replay_attempts"], 1)
        self.assertEqual(result["daily_rejected_attempts"], 1)
        self.assertEqual(result["daily_non_successful_d1_query_attempts"], 4)
        self.assertEqual(result["daily_prepaid_meter_debits"], 7)
        self.assertEqual(result["daily_resource_demand_including_meter"], {
            "provider_requests": 3,
            "r2_class_a": 6,
            "r2_class_b": 3,
            "r2_new_bytes": 384,
            "d1_queries": 17,
            "d1_rows_read": 31,
            "d1_rows_written": 28,
            "d1_storage_growth_bytes": 748,
        })
        self.assertEqual(result["rolling_resource_demand"], {
            "r2_class_a": 186,
            "r2_class_b": 93,
            "r2_new_bytes": 11904,
        })
        self.assertEqual(result["projected_new_d1_storage_bytes_in_window_not_total"], 748 * 31)
        self.assertEqual(result["reservations_retained_if_no_compaction"], 93)
        for field in (
            "approved_account_caps_proven",
            "account_usage_and_headroom_fresh",
            "writer_inventory_complete_proven",
            "d1_provisioned",
            "durable_prepaid_controller_implemented_and_calibrated",
            "real_account_storage_baseline_known",
            "zero_usd_monthly_cost_proven",
            "production_execution_authority",
            "paper_activation_allowed",
            "real_money_order_authority",
        ):
            with self.subTest(field=field):
                self.assertIs(result[field], False)

    def test_unknown_caps_fail_closed_without_inventing_zero_dollar_safety(self) -> None:
        for scenario in (None, {}, {"daily": {}, "rolling_31_days": {}},
                         {"daily": {"reservations": 1}, "rolling_31_days": {}}):
            with self.subTest(caps=scenario):
                result = forecast_shared_budget(
                    writers=self.writers(), query_attempt_cost=self.meter(),
                    hypothetical_caps=scenario,
                )
                self.assertEqual(result["status"], "BLOCKED_UNKNOWN_CAPS")
                self.assertFalse(result["zero_usd_monthly_cost_proven"])

    def test_overflow_blocks_on_every_daily_dimension_including_meter(self) -> None:
        caps = self.caps()
        for metric in (
            "reservations", "provider_requests", "r2_class_a", "r2_class_b",
            "r2_new_bytes", "d1_queries", "d1_rows_read", "d1_rows_written",
            "d1_storage_growth_bytes",
        ):
            tighter = {
                "daily": {**caps["daily"], metric: caps["daily"][metric] - 1},
                "rolling_31_days": dict(caps["rolling_31_days"]),
            }
            with self.subTest(metric=metric):
                result = forecast_shared_budget(
                    writers=self.writers(), query_attempt_cost=self.meter(),
                    hypothetical_caps=tighter,
                )
                self.assertEqual(result["status"], "BLOCKED_SCENARIO_OVER_CAP")
                self.assertIn("daily." + metric, result["hypothetical_cap_violations"])

    def test_rolling_caps_are_not_replaced_by_daily_caps(self) -> None:
        caps = self.caps()
        for metric in ("r2_class_a", "r2_class_b", "r2_new_bytes"):
            tighter = {
                "daily": dict(caps["daily"]),
                "rolling_31_days": {**caps["rolling_31_days"],
                                    metric: caps["rolling_31_days"][metric] - 1},
            }
            with self.subTest(metric=metric):
                output = forecast_shared_budget(
                    writers=self.writers(), query_attempt_cost=self.meter(),
                    hypothetical_caps=tighter,
                )
                self.assertIn(
                    "rolling_31_days." + metric,
                    output["hypothetical_cap_violations"],
                )

    def test_failed_attempts_are_charged_even_without_successful_work(self) -> None:
        failed = replace(
            self.writers()[0], successful_slots_per_day=0,
            replay_attempts_per_day=0, rejected_attempts_per_day=2,
        )
        result = forecast_shared_budget(
            writers=[failed], query_attempt_cost=self.meter(),
        )
        self.assertEqual(result["daily_successful_reservations"], 0)
        self.assertEqual(result["daily_non_successful_d1_query_attempts"], 4)
        self.assertEqual(result["daily_prepaid_meter_debits"], 4)
        self.assertEqual(result["daily_resource_demand_including_meter"]["d1_queries"], 8)
        self.assertEqual(result["daily_resource_demand_including_meter"]["d1_rows_written"], 4)
        self.assertEqual(result["status"], "BLOCKED_UNKNOWN_CAPS")

    def test_invalid_envelope_writer_and_meter_fail_before_forecasting(self) -> None:
        bad_cases = (
            [replace(self.writers()[0], writer_id="")],
            [self.writers()[0], replace(self.writers()[0], successful_slots_per_day=1)],
            [replace(self.writers()[0], successful_slots_per_day=True)],
            [replace(self.writers()[0], per_success_slot=replace(self.slot(), d1_queries=1))],
            [replace(self.writers()[0], per_success_slot=replace(self.slot(), d1_rows_written=6))],
            [replace(self.writers()[0], per_success_slot=replace(self.slot(), r2_new_bytes=-1))],
        )
        for rows in bad_cases:
            with self.subTest(writers=rows), self.assertRaises(ValueError):
                forecast_shared_budget(writers=rows, query_attempt_cost=self.meter())
        for invalid in (
            replace(self.meter(), control_d1_queries=0),
            replace(self.meter(), control_d1_rows_read=True),
        ):
            with self.assertRaises(ValueError):
                forecast_shared_budget(writers=self.writers(), query_attempt_cost=invalid)

        with self.assertRaisesRegex(ValueError, "WRITER_COUNT_INVALID"):
            forecast_shared_budget(writers=[], query_attempt_cost=self.meter())
        with self.assertRaisesRegex(ValueError, "WINDOW_EXCEEDS_31_DAYS"):
            forecast_shared_budget(
                writers=self.writers(), query_attempt_cost=self.meter(),
                window_days=32,
            )

    def test_shorter_window_does_not_change_daily_budget_and_still_no_production(self) -> None:
        output = forecast_shared_budget(
            writers=self.writers(), query_attempt_cost=self.meter(),
            hypothetical_caps=self.caps(), window_days=1,
        )
        self.assertEqual(output["daily_resource_demand_including_meter"]["d1_queries"], 17)
        self.assertEqual(output["rolling_resource_demand"]["r2_class_a"], 6)
        self.assertEqual(output["reservations_retained_if_no_compaction"], 3)
        self.assertFalse(output["paper_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
