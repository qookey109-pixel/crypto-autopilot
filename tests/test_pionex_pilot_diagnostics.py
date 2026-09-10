"""Offline request-context regressions; no provider or storage clients."""
import runpy
import unittest
from pathlib import Path


MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/run_pionex_historical_research_execution_v0_1.py"))


class FakeClient:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def get_klines(self, symbol, interval, **kwargs):
        self.calls.append((symbol, interval, kwargs))
        result = next(self.pages)
        if isinstance(result, Exception):
            raise result
        return result


class DiagnosticTests(unittest.TestCase):
    def test_bootstrap_failure_is_sanitized_and_not_retried(self):
        client = FakeClient([RuntimeError("MARKET_INVALID_TIME sensitive-error-detail")])
        wrapper = MODULE["PilotKlineDiagnostics"](client)
        with self.assertRaises(MODULE["PilotAuthorityError"]) as caught:
            wrapper.get_klines("BTC_USDT_PERP", "15M")
        self.assertIn("phase=bootstrap", str(caught.exception))
        self.assertIn("request=1", str(caught.exception))
        self.assertNotIn("sensitive-error-detail", str(caught.exception))
        self.assertEqual(len(client.calls), 1)

    def test_pagination_context_and_rows_are_separate_per_interval(self):
        page = [object(), object()]
        client = FakeClient([page, [], RuntimeError("MARKET_INVALID_TIME")])
        wrapper = MODULE["PilotKlineDiagnostics"](client)
        self.assertIs(wrapper.get_klines("BTC_USDT_PERP", "15M"), page)
        wrapper.get_klines("BTC_USDT_PERP", "4H")
        with self.assertRaises(MODULE["PilotAuthorityError"]) as caught:
            wrapper.get_klines("BTC_USDT_PERP", "15M", end_time_ms=123, limit=2)
        self.assertIn("request=2", str(caught.exception))
        self.assertIn("phase=pagination", str(caught.exception))
        self.assertIn("returned_rows_before_failure=2", str(caught.exception))
        self.assertEqual(client.calls[-1][2], {"end_time_ms": 123, "limit": 2})
        self.assertEqual(len(client.calls), 3)


if __name__ == "__main__":
    unittest.main()
