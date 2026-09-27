from __future__ import annotations

import unittest

from crypto_autopilot.storage.r2 import R2Store


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
) -> R2Store:
    result = R2Store.__new__(R2Store)
    result.client = client
    result.bucket = "fixture-bucket"
    result.before_external = before_external or (
        lambda operation, size: reservations.append((operation, size))
    )
    return result


class R2BudgetHookTests(unittest.TestCase):
    def test_read_write_and_conditional_write_reserve_before_request(self):
        client = FakeClient()
        reservations: list[tuple[str, int]] = []
        r2 = store(client, reservations)

        write = r2.put_bytes("paper/a.json", b"data")
        read = r2.get_bytes_if_exists("paper/a.json")
        conditional = r2.put_bytes_if_absent("paper/b.json", b"abc")

        self.assertEqual(write.bytes, 4)
        self.assertEqual(read, b"data")
        self.assertEqual(conditional.bytes, 3)
        self.assertEqual(
            reservations,
            [("R2_CLASS_A", 4), ("R2_CLASS_B", 0), ("R2_CLASS_A", 3)],
        )
        self.assertEqual(
            [name for name, _ in client.calls],
            ["put_object", "get_object", "put_object"],
        )

    def test_budget_rejection_prevents_client_call(self):
        client = FakeClient()

        def reject(operation: str, size: int) -> None:
            raise RuntimeError("blocked before R2")

        r2 = store(client, [], before_external=reject)
        with self.assertRaisesRegex(RuntimeError, "blocked before R2"):
            r2.get_bytes_if_exists("paper/missing.json")
        self.assertEqual(client.calls, [])

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
