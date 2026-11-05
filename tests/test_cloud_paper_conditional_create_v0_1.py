"""Cloud Paper concurrent create tests; no external R2 access."""
import threading
import unittest
from types import SimpleNamespace

from crypto_autopilot.paper.cloud_run_store_v0_1 import CloudPaperRunStore


class PreconditionFailed(Exception):
    response = {"Error": {"Code": "PreconditionFailed"},
                "ResponseMetadata": {"HTTPStatusCode": 412}}


class FakeStore:
    def __init__(self, concurrent=False):
        self.bucket = "test-bucket"
        self.client = self
        self.objects = {}
        self.lock = threading.Lock()
        self.initial_reads = 0
        self.barrier = threading.Barrier(2) if concurrent else None
        self.calls = []
        self.timeout = False

    def get_bytes_if_exists(self, key):
        with self.lock:
            value = self.objects.get(key)
            self.initial_reads += 1
            first_reads = self.initial_reads <= 2
        if self.barrier and first_reads:
            self.barrier.wait(timeout=5)
        return value

    def put_bytes(self, key, body, **kwargs):
        with self.lock:
            self.calls.append({"unconditional": True})
            self.objects[key] = body
        return SimpleNamespace(bytes=len(body))

    def put_object(self, **kwargs):
        with self.lock:
            self.calls.append(kwargs)
            if self.timeout:
                raise TimeoutError("ambiguous transport")
            if kwargs.get("IfNoneMatch") != "*":
                raise AssertionError("write was not conditional")
            if kwargs["Key"] in self.objects:
                raise PreconditionFailed()
            self.objects[kwargs["Key"]] = kwargs["Body"]
        return {}


class CloudPaperAtomicCreateTests(unittest.TestCase):
    def test_concurrent_conflicting_payloads_do_not_overwrite(self):
        backend = FakeStore(concurrent=True)
        store = CloudPaperRunStore(backend)
        outcomes = []
        def run(value):
            try:
                outcomes.append(store.put_json("result", "same-id", {"value": value}))
            except ValueError:
                outcomes.append("collision")
        threads = [threading.Thread(target=run, args=(value,)) for value in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes.count("collision"), 1)
        self.assertEqual(len(backend.objects), 1)
        self.assertEqual(len(backend.calls), 2)
        self.assertTrue(all(call.get("IfNoneMatch") == "*" for call in backend.calls))

    def test_concurrent_identical_payload_returns_one_replay(self):
        backend = FakeStore(concurrent=True)
        store = CloudPaperRunStore(backend)
        outcomes = []
        def run():
            outcomes.append(store.put_json("result", "same-id", {"value": 1}))
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(sorted(item.replayed for item in outcomes), [False, True])
        self.assertTrue(all(call.get("IfNoneMatch") == "*" for call in backend.calls))

    def test_ambiguous_write_is_not_retried_or_treated_as_absent(self):
        backend = FakeStore()
        backend.timeout = True
        with self.assertRaises(TimeoutError):
            CloudPaperRunStore(backend).put_json("result", "same-id", {"value": 1})
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(backend.initial_reads, 1)
        self.assertEqual(backend.calls[0].get("IfNoneMatch"), "*")
