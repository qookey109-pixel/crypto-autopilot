"""Bounded reads for Cloud Paper's budgeted R2 adapter."""
import hashlib
import unittest
from io import BytesIO
from unittest.mock import Mock

from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Policy, BudgetedR2Store


class BoundedPaperReads(unittest.TestCase):
    def test_read_limit_applies_to_verified_and_optional_reads(self):
        for method in ("get_bytes_verified", "get_bytes_if_exists"):
            for data, allowed in ((b"1234", True), (b"12345", False)):
                with self.subTest(method=method, size=len(data)):
                    body = BytesIO(data)
                    client = Mock()
                    client.get_object.return_value = {"Body": body, "Metadata": {}}
                    requests = []
                    store = BudgetedR2Store(
                        client=client, bucket="fixture",
                        before_external=lambda operation, size: requests.append((operation, size)),
                        policy=BudgetedR2Policy(maximum_read_bytes=4),
                    )
                    kwargs = {"expected_sha256": hashlib.sha256(data).hexdigest()} if method == "get_bytes_verified" else {}
                    if allowed:
                        self.assertEqual(getattr(store, method)("fixture", **kwargs), data)
                    else:
                        with self.assertRaises(ValueError):
                            getattr(store, method)("fixture", **kwargs)
                    self.assertTrue(body.closed)
                    self.assertEqual(requests, [("R2_CLASS_B", 0)])

    def test_unbounded_legacy_adapter_remains_compatible(self):
        client = Mock()
        client.get_object.return_value = {"Body": BytesIO(b"legacy"), "Metadata": {}}
        store = BudgetedR2Store(client=client, bucket="fixture", before_external=lambda *args: None)
        self.assertEqual(store.get_bytes_if_exists("fixture"), b"legacy")
