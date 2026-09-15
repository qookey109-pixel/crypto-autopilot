from __future__ import annotations

import unittest

from crypto_autopilot.toolkit.http_api import dispatch_request, openapi_document


class QookeyCryptoToolkitHttpV01Tests(unittest.TestCase):
    def test_health_is_research_only_and_fail_closed(self) -> None:
        status, body = dispatch_request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "PASS")
        self.assertEqual(body["mode"], "RESEARCH_ONLY")
        self.assertTrue(all(value is False for value in body["authority"].values()))

    def test_capabilities_route_exposes_existing_registry(self) -> None:
        status, body = dispatch_request("GET", "/v0/capabilities")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "RESEARCH_ONLY")
        self.assertTrue(all(value is False for value in body["safety_boundary"].values()))

    def test_indicators_route_uses_toolkit_aliases(self) -> None:
        candles = []
        for index in range(240):
            close = 100.0 + index * 0.1
            candles.append(
                {
                    "time_ms": index * 3_600_000,
                    "open": close - 0.2,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1_000.0 + index,
                }
            )
        status, body = dispatch_request(
            "POST",
            "/v0/indicators",
            {"interval": "1h", "candles": candles},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["canonical_interval"], "60M")
        self.assertTrue(body["latest_ready_v0_2"])
        self.assertTrue(all(value is False for value in body["authority"].values()))

    def test_invalid_payload_fails_closed_with_400(self) -> None:
        status, body = dispatch_request("POST", "/v0/indicators", {"interval": "1h"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "INVALID_TOOL_INPUT")
        self.assertTrue(all(value is False for value in body["authority"].values()))

    def test_method_and_unknown_routes_are_explicit(self) -> None:
        status, body = dispatch_request("GET", "/v0/risk")
        self.assertEqual(status, 405)
        self.assertEqual(body["error"]["code"], "METHOD_NOT_ALLOWED")

        status, body = dispatch_request("GET", "/v0/does-not-exist")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")

    def test_openapi_lists_all_supported_routes(self) -> None:
        document = openapi_document()
        self.assertEqual(document["openapi"], "3.1.0")
        self.assertEqual(
            set(document["paths"]),
            {
                "/healthz",
                "/v0/capabilities",
                "/v0/indicators",
                "/v0/strategy",
                "/v0/risk",
                "/v0/backtest",
            },
        )
        for path in ("/v0/indicators", "/v0/strategy", "/v0/risk", "/v0/backtest"):
            self.assertEqual(document["paths"][path]["post"]["security"], [{"bearerAuth": []}])


if __name__ == "__main__":
    unittest.main()
