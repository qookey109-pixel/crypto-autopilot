from __future__ import annotations

import unittest

from crypto_autopilot.storage.r2 import R2Store


class _FakeClient:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        self.calls.append((Bucket, Key))
        if self.error is not None:
            raise self.error
        return {}


class _FakeClientError(Exception):
    def __init__(self, *, code: str = "", status: int | None = None) -> None:
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }


def _store(client: _FakeClient) -> R2Store:
    store = object.__new__(R2Store)
    store.bucket = "test-bucket"
    store.client = client
    return store


class R2StoreExistsTests(unittest.TestCase):
    def test_existing_key_uses_head_only_and_returns_true(self) -> None:
        client = _FakeClient()
        store = _store(client)

        self.assertTrue(store.exists("path/object.json"))
        self.assertEqual(client.calls, [("test-bucket", "path/object.json")])

    def test_missing_key_returns_false_for_not_found_code(self) -> None:
        client = _FakeClient(error=_FakeClientError(code="NoSuchKey", status=404))
        store = _store(client)

        self.assertFalse(store.exists("missing.json"))

    def test_non_not_found_error_is_not_swallowed(self) -> None:
        error = _FakeClientError(code="AccessDenied", status=403)
        client = _FakeClient(error=error)
        store = _store(client)

        with self.assertRaises(_FakeClientError):
            store.exists("forbidden.json")


if __name__ == "__main__":
    unittest.main()
