import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

from crypto_autopilot.models import Candle
from crypto_autopilot.history.pionex_bounded_pilot import PilotRejected, collect, stamp, require_window, digest
from crypto_autopilot.historical import INTERVAL_MS

ROOT = Path(__file__).resolve().parents[1]
RUNNER = runpy.run_path(str(ROOT / "scripts/run_pionex_historical_research_execution_v0_2.py"))


class Provider:
    def __init__(self, mode="good"):
        self.calls = []
        self.mode = mode

    def get_klines(self, symbol, interval, *, limit, end_time_ms):
        self.calls.append((symbol, interval, limit, end_time_ms))
        if self.mode == "error":
            raise RuntimeError("MARKET_INVALID_TIME secret-detail")
        step = INTERVAL_MS[interval]
        page = [Candle(t, 1, 2, 1, 2, 10) for t in range(end_time_ms - (limit - 1) * step, end_time_ms + 1, step)]
        if self.mode == "gap":
            page.pop(1)
        elif self.mode == "duplicate":
            page[1] = page[0]
        elif self.mode == "out_of_range":
            page[-1] = Candle(stamp("2026-08-28T00:00:00Z"), 1, 2, 1, 2, 10)
        elif self.mode == "shifted":
            page = [Candle(c.time_ms - step, 1, 2, 1, 2, 10) for c in page]
        return page


class BoundedPilotTests(unittest.TestCase):
    def setUp(self):
        self.config = RUNNER["load_authority"]()
        self.clock = lambda: stamp("2026-09-10T16:00:00Z")
        self.progress = {"requests": 0, "holdout_accessed": False}

    def test_exact_range_and_no_holdout_bootstrap(self):
        provider = Provider()
        data = collect(self.config, provider, self.clock, self.progress)
        self.assertEqual({key: len(value) for key, value in data.items()}, {"15M": 2592, "60M": 648, "4H": 162})
        self.assertEqual(len(provider.calls), 9)
        for _, interval, limit, end in provider.calls:
            self.assertLess(end, stamp("2026-08-28T00:00:00Z"))
            self.assertGreaterEqual(end - (limit - 1) * INTERVAL_MS[interval], stamp("2026-08-01T00:00:00Z"))

    def test_provider_error_never_becomes_eof_or_retry(self):
        provider = Provider("error")
        with self.assertRaises(PilotRejected) as caught:
            collect(self.config, provider, self.clock, self.progress)
        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn("secret-detail", str(caught.exception))

    def test_gap_duplicate_and_wrong_endpoints_fail(self):
        for mode in ("gap", "duplicate", "shifted"):
            with self.subTest(mode=mode), self.assertRaises(PilotRejected):
                collect(self.config, Provider(mode), self.clock, {"requests": 0})

    def test_unexpected_protected_response_is_not_certified_unopened(self):
        with self.assertRaises(PilotRejected):
            collect(self.config, Provider("out_of_range"), self.clock, self.progress)
        self.assertEqual(self.progress["holdout_accessed"], "UNVERIFIED_PROVIDER_RANGE_VIOLATION")

    def test_range_and_expiry_checked_before_first_request(self):
        for change in ({"end_exclusive_utc": "2026-09-04T00:00:00Z"},
                       {"start_utc": "2026-01-01T00:00:00Z"},
                       {"stop_exclusive_utc": "2026-09-10T15:00:00Z"}):
            provider = Provider()
            with self.subTest(change=change), self.assertRaises(PilotRejected):
                collect({**self.config, **change}, provider, self.clock, self.progress)
            self.assertEqual(provider.calls, [])

    def test_expiry_is_rechecked_between_pages(self):
        times = iter([self.clock(), stamp("2026-09-24T00:00:00Z")])
        provider = Provider()
        with self.assertRaises(PilotRejected):
            collect(self.config, provider, lambda: next(times), self.progress)
        self.assertEqual(len(provider.calls), 1)

    def test_request_budget_stops_before_extra_request(self):
        provider = Provider()
        with self.assertRaises(PilotRejected):
            collect({**self.config, "maximum_requests": 1}, provider, self.clock, self.progress)
        self.assertEqual(len(provider.calls), 1)

    def test_same_window_is_inside_horizon_until_expiry(self):
        require_window(self.config, lambda: stamp("2026-09-23T23:59:59Z"))

    def test_only_existing_manual_workflow_is_used(self):
        workflow = (ROOT / ".github/workflows/pionex-historical-research-execution-v0-1.yml").read_text()
        self.assertIn("run_pionex_historical_research_execution_v0_2.py", workflow)
        self.assertNotIn("run_pionex_historical_research_execution_v0_1.py", workflow)
        self.assertNotIn("  schedule:", workflow)
        receipt = json.loads((ROOT / "research/receipts/2026-09-10-pionex-bounded-pilot-v0-2-authority.json").read_text())
        self.assertFalse(receipt["execution_performed_by_this_receipt"])


class Store:
    def __init__(self, fail_at=0):
        self.data = {}
        self.writes = []
        self.fail_at = fail_at

    def get_bytes_if_exists(self, key):
        return self.data.get(key)

    def put_bytes(self, key, data, **kwargs):
        self.writes.append(key)
        if len(self.writes) == self.fail_at:
            raise RuntimeError("storage failure")
        self.data[key] = data

    def get_bytes_verified(self, key, *, expected_sha256):
        data = self.data[key]
        if digest(data) != expected_sha256:
            raise ValueError("hash mismatch")
        return data


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.config = RUNNER["load_authority"]()
        self.clock = lambda: stamp("2026-09-10T16:00:00Z")
        self.progress = {"requests": 0, "r2_writes_performed": False, "holdout_accessed": False}
        self.store = Store()
        self.provider = Provider()
        self.budget = patch("crypto_autopilot.training.online_r2.current_bucket_bytes", return_value=0)
        self.budget_mock = self.budget.start()
        self.addCleanup(self.budget.stop)

    def run_pilot(self):
        return RUNNER["execute"](self.config, self.store, self.provider, "github-123-1", self.progress, clock=self.clock)

    def test_publication_roundtrip_receipt_binding_pointer_last_and_one_shot(self):
        report = self.run_pilot()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(self.store.writes), 5)
        self.assertTrue(self.store.writes[-1].endswith("/latest.json"))
        self.assertEqual(self.budget_mock.call_count, 6)
        for entry in report["intervals"]:
            self.assertEqual(digest(self.store.data[entry["key"]]), entry["sha256"])
        self.assertEqual(self.run_pilot()["status"], "ALREADY_COMPLETE")
        self.assertEqual(len(self.provider.calls), 9)
        self.assertEqual(len(self.store.writes), 5)

    def test_budget_fails_before_provider(self):
        self.budget_mock.return_value = 8_000_000_000
        with self.assertRaises(PilotRejected):
            self.run_pilot()
        self.assertFalse(self.provider.calls)
        self.assertFalse(self.store.writes)

    def test_failed_collection_never_writes(self):
        self.provider.mode = "gap"
        with self.assertRaises(PilotRejected):
            self.run_pilot()
        self.assertFalse(self.store.writes)

    def test_write_failure_cannot_claim_zero_writes_or_complete(self):
        self.store.fail_at = 2
        with self.assertRaises(RuntimeError):
            self.run_pilot()
        self.assertEqual(self.progress["r2_writes_performed"], "UNKNOWN_WRITE_ATTEMPTED")
        self.assertFalse(any(key.endswith("/latest.json") for key in self.store.data))

    def test_expiry_before_publication_leaves_no_writes(self):
        # Start gate, headroom gate, nine pages, first-write gate.
        times = iter([self.clock()] * 11 + [stamp("2026-09-24T00:00:00Z")])
        self.clock = lambda: next(times)
        with self.assertRaises(PilotRejected):
            self.run_pilot()
        self.assertFalse(self.store.writes)

    def test_partial_target_conflict_and_pointer_escape_fail_closed(self):
        self.store.data[self.config["namespace"] + "/run=github-123-1/15M.parquet"] = b"partial"
        with self.assertRaises(PilotRejected):
            self.run_pilot()
        self.assertFalse(self.store.writes)
        self.store.data[self.config["namespace"] + "/latest.json"] = b'{"receipt_key":"outside/receipt.json"}'
        with self.assertRaises(PilotRejected):
            self.run_pilot()


if __name__ == "__main__":
    unittest.main()
