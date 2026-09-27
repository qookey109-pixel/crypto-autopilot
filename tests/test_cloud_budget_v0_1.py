from __future__ import annotations

import unittest
from dataclasses import replace

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetGuard,
    CloudBudgetPolicy,
    R2UsageSnapshot,
)


NOW = 1_000_000


def snapshot(**changes: object) -> R2UsageSnapshot:
    base = R2UsageSnapshot(
        account_wide=True,
        reservation_coverage_complete=True,
        observed_at_ms=NOW,
        measured_through_ms=NOW,
        storage_bytes=0,
        class_a_month=0,
        class_b_month=0,
        class_a_31_days=0,
        class_b_31_days=0,
        class_a_day=0,
        class_b_day=0,
        provider_requests_day=0,
        new_bytes_day=0,
    )
    return replace(base, **changes)


class CloudBudgetGuardTests(unittest.TestCase):
    def test_fresh_complete_snapshot_reserves_each_operation(self):
        guard = CloudBudgetGuard(snapshot=snapshot(), now_ms=NOW)
        guard.reserve_provider_request()
        guard.reserve_r2_class_a(new_bytes=100)
        guard.reserve_r2_class_b()

    def test_missing_account_wide_evidence_blocks_before_reservation(self):
        guard = CloudBudgetGuard(snapshot=snapshot(account_wide=False), now_ms=NOW)
        with self.assertRaisesRegex(BudgetBlocked, "EVIDENCE_INCOMPLETE"):
            guard.reserve_provider_request()

    def test_untracked_account_activity_blocks(self):
        guard = CloudBudgetGuard(
            snapshot=snapshot(reservation_coverage_complete=False), now_ms=NOW
        )
        with self.assertRaisesRegex(BudgetBlocked, "EVIDENCE_INCOMPLETE"):
            guard.reserve_r2_class_a()

    def test_stale_observation_and_stale_measurement_block(self):
        policy = CloudBudgetPolicy(max_evidence_age_ms=60_000)
        for values in (
            {"observed_at_ms": NOW - 60_001},
            {"measured_through_ms": NOW - 60_001},
        ):
            guard = CloudBudgetGuard(
                snapshot=snapshot(**values), now_ms=NOW, policy=policy
            )
            with self.assertRaisesRegex(BudgetBlocked, "EVIDENCE_STALE"):
                guard.reserve_r2_class_b()

    def test_daily_limit_includes_operations_reserved_in_this_run(self):
        guard = CloudBudgetGuard(
            snapshot=snapshot(class_a_day=12_287, class_a_month=500_000),
            now_ms=NOW,
        )
        guard.reserve_r2_class_a()
        with self.assertRaisesRegex(BudgetBlocked, "CLASS_A_DAILY_LIMIT"):
            guard.reserve_r2_class_a()

    def test_rolling_31_day_limit_blocks(self):
        guard = CloudBudgetGuard(
            snapshot=snapshot(class_b_31_days=380_928), now_ms=NOW
        )
        with self.assertRaisesRegex(BudgetBlocked, "CLASS_B_31_DAY_LIMIT"):
            guard.reserve_r2_class_b()

    def test_account_free_and_project_monthly_limits_block(self):
        for count in (750_000, 1_000_000):
            guard = CloudBudgetGuard(
                snapshot=snapshot(class_a_month=count), now_ms=NOW
            )
            with self.assertRaisesRegex(BudgetBlocked, "CLASS_A_MONTHLY_LIMIT"):
                guard.reserve_r2_class_a()

    def test_object_run_day_and_storage_limits_block(self):
        policy = CloudBudgetPolicy(r2_new_bytes_per_run=100)
        oversized_guard = CloudBudgetGuard(
            snapshot=snapshot(), now_ms=NOW, policy=policy
        )
        with self.assertRaisesRegex(BudgetBlocked, "OBJECT_LIMIT"):
            oversized_guard.reserve_r2_class_a(new_bytes=262_145)

        run_guard = CloudBudgetGuard(
            snapshot=snapshot(), now_ms=NOW, policy=policy
        )
        run_guard.reserve_r2_class_a(new_bytes=100)
        with self.assertRaisesRegex(BudgetBlocked, "RUN_BYTES_LIMIT"):
            run_guard.reserve_r2_class_a(new_bytes=1)

        daily_guard = CloudBudgetGuard(
            snapshot=snapshot(new_bytes_day=201_326_592), now_ms=NOW
        )
        with self.assertRaisesRegex(BudgetBlocked, "DAILY_BYTES_LIMIT"):
            daily_guard.reserve_r2_class_a(new_bytes=1)

        storage_guard = CloudBudgetGuard(
            snapshot=snapshot(storage_bytes=8_000_000_000), now_ms=NOW
        )
        with self.assertRaisesRegex(BudgetBlocked, "STORAGE_HARD_STOP"):
            storage_guard.reserve_r2_class_a(new_bytes=1)

    def test_unknown_or_negative_usage_blocks(self):
        for value in (None, -1, True):
            guard = CloudBudgetGuard(
                snapshot=snapshot(class_b_month=value), now_ms=NOW
            )
            with self.assertRaisesRegex(BudgetBlocked, "USAGE_UNKNOWN"):
                guard.reserve_r2_class_b()

    def test_provider_daily_and_per_run_ceiling(self):
        policy = CloudBudgetPolicy(provider_per_run=2, provider_per_day=3)
        guard = CloudBudgetGuard(
            snapshot=snapshot(provider_requests_day=1), now_ms=NOW, policy=policy
        )
        guard.reserve_provider_request()
        guard.reserve_provider_request()
        with self.assertRaisesRegex(BudgetBlocked, "PROVIDER_RUN_LIMIT"):
            guard.reserve_provider_request()

    def test_provider_daily_ceiling_blocks(self):
        guard = CloudBudgetGuard(
            snapshot=snapshot(provider_requests_day=1_728), now_ms=NOW
        )
        with self.assertRaisesRegex(BudgetBlocked, "PROVIDER_DAILY_LIMIT"):
            guard.reserve_provider_request()


if __name__ == "__main__":
    unittest.main()
