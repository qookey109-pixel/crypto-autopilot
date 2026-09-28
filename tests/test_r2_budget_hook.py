from __future__ import annotations

import unittest

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetGuard,
    CloudBudgetPolicy,
    R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore


class FakeBody:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.pages: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> dict[str, str]:
        self.calls.append(("put_object", kwargs))
        return {"ETag": '"fixture-etag"'}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_object", kwargs))
        return {"Body": FakeBody(b"data"), "Metadata": {}}

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("list_objects_v2", kwargs))
        return self.pages.pop(0)


def store(
    client: FakeClient,
    reservations: list[tuple[str, int]],
    before_external=None,
) -> BudgetedR2Store:
    return BudgetedR2Store(
        client=client,
        bucket="fixture-bucket",
        before_external=before_external or (
            lambda operation, size: reservations.append((operation, size))
        ),
    )


class R2BudgetHookTests(unittest.TestCase):
    def test_reads_writes_and_conditional_creates_reserve_before_requests(self):
        client = FakeClient()
        reservations: list[tuple[str, int]] = []
        r2 = store(client, reservations)
        run_store = R2PaperRunStore(r2)

        write = r2.put_bytes("paper/a.json", b"data")
        read = r2.get_bytes_if_exists("paper/a.json")
        conditional = run_store.put_json_if_absent(
            "live-run-claim", "slot-1", {"schema": "fixture", "value": 1}
        )

        self.assertEqual(write.bytes, 4)
        self.assertEqual(read, b"data")
        self.assertEqual(conditional.bytes, len(
            b'{"schema":"fixture","value":1}'
        ))
        self.assertEqual(
            [operation for operation, _ in reservations],
            ["R2_CLASS_A", "R2_CLASS_B", "R2_CLASS_A"],
        )
        self.assertEqual(
            [name for name, _ in client.calls],
            ["put_object", "get_object", "put_object"],
        )

    def test_list_reserves_each_page_and_stops_after_last_page(self):
        client = FakeClient()
        client.pages = [
            {
                "Contents": [{"Key": "paper/a.json"}],
                "IsTruncated": True,
                "NextContinuationToken": "page-2",
            },
            {"Contents": [{"Key": "paper/b.json"}], "IsTruncated": False},
        ]
        reservations: list[tuple[str, int]] = []
        r2 = store(client, reservations)

        keys = r2.list_keys("paper/")

        self.assertEqual(keys, ("paper/a.json", "paper/b.json"))
        self.assertEqual(reservations, [("R2_CLASS_A", 0), ("R2_CLASS_A", 0)])
        self.assertEqual(len(client.calls), 2)
        self.assertNotIn("ContinuationToken", client.calls[0][1])
        self.assertEqual(client.calls[1][1]["ContinuationToken"], "page-2")

    def test_cloud_budget_guard_blocks_before_r2_io(self):
        now_ms = 1_000_000
        guard = CloudBudgetGuard(
            snapshot=R2UsageSnapshot(
                account_wide=True,
                reservation_coverage_complete=True,
                observed_at_ms=now_ms,
                measured_through_ms=now_ms,
                storage_bytes=0,
                class_a_month=0,
                class_b_month=0,
                class_a_31_days=0,
                class_b_31_days=0,
                class_a_day=0,
                class_b_day=0,
                provider_requests_day=0,
                new_bytes_day=0,
            ),
            clock_ms=lambda: now_ms,
            policy=CloudBudgetPolicy(r2_class_a_per_run=0),
        )
        client = FakeClient()
        budgeted = BudgetedR2Store(
            client=client, bucket="fixture-bucket", budget_guard=guard,
        )
        run_store = R2PaperRunStore(budgeted)
        self.assertIs(run_store.store.budget_guard, guard)

        with self.assertRaisesRegex(BudgetBlocked, "CLASS_A_RUN_LIMIT"):
            run_store.put_json_if_absent(
                "live-run-claim", "slot-1", {"schema": "fixture"}
            )

        self.assertEqual(client.calls, [])

    def test_malformed_pagination_fails_after_bounded_reservation(self):
        client = FakeClient()
        client.pages = [
            {"Contents": [], "IsTruncated": True, "NextContinuationToken": ""}
        ]
        reservations: list[tuple[str, int]] = []
        r2 = store(client, reservations)

        with self.assertRaisesRegex(ValueError, "continuation token"):
            r2.list_keys("paper/")

        self.assertEqual(reservations, [("R2_CLASS_A", 0)])


if __name__ == "__main__":
    unittest.main()
