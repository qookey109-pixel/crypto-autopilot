from __future__ import annotations

import unittest

from crypto_autopilot.toolkit.http_api import dispatch_request, openapi_document


def _candles() -> list[dict[str, float | int]]:
    return [
        {
            "time_ms": 0,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10.0,
        },
        {
            "time_ms": 60_000,
            "open": 100.0,
            "high": 106.0,
            "low": 99.0,
            "close": 105.0,
            "volume": 12.0,
        },
    ]


def _backtest_payload(*, fee_bps: float = 0.0, slippage_bps: float = 0.0) -> dict:
    return {
        "candles_by_symbol": {"BTCUSDT": _candles()},
        "plans": [
            {
                "plan_id": "paper-1",
                "symbol": "BTCUSDT",
                "signal_time_ms": 0,
                "stop_price": 95.0,
                "target_price": 105.0,
            }
        ],
        "config": {
            "taker_fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
        },
    }


class QookeyCryptoToolkitHttpV02Tests(unittest.TestCase):
    def test_health_and_capabilities_are_v02_research_only(self) -> None:
        status, health = dispatch_request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(health["schema"], "qookey-crypto-toolkit-api-health-v0.2")
        self.assertEqual(health["toolkit_version"], "0.2")
        self.assertTrue(all(value is False for value in health["authority"].values()))

        status, capabilities = dispatch_request("GET", "/v0/capabilities")
        self.assertEqual(status, 200)
        self.assertEqual(capabilities["schema"], "qookey-crypto-toolkit-capabilities-v0.2")
        self.assertEqual(capabilities["interfaces"]["rest_api"], "IMPLEMENTED_PREPARED_RESEARCH_ONLY")
        self.assertEqual(len(capabilities["tools"]), 8)
        self.assertTrue(all(value is False for value in capabilities["safety_boundary"].values()))

    def test_validate_route_preserves_failed_gap_without_repair(self) -> None:
        status, body = dispatch_request(
            "POST",
            "/v0/validate",
            {
                "interval": "1h",
                "candles": [
                    _candles()[0],
                    {
                        "time_ms": 7_200_000,
                        "open": 101.0,
                        "high": 102.0,
                        "low": 100.0,
                        "close": 101.0,
                        "volume": 11.0,
                    },
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "FAIL")
        self.assertEqual(body["gap_count"], 1)
        self.assertFalse(body["repair_performed"])
        self.assertFalse(body["interpolation_performed"])
        self.assertTrue(all(value is False for value in body["authority"].values()))

    def test_stress_compare_and_report_routes_use_existing_v02_tools(self) -> None:
        status, stress = dispatch_request(
            "POST",
            "/v0/stress",
            {
                "backtest": _backtest_payload(),
                "scenarios": [
                    {"name": "base", "taker_fee_bps": 0.0, "slippage_bps": 0.0},
                    {"name": "cost", "taker_fee_bps": 10.0, "slippage_bps": 10.0},
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(stress["schema"], "qookey-crypto-toolkit-stress-backtest-v0.2")
        self.assertEqual(stress["scenario_count"], 2)
        self.assertFalse(stress["automatic_strategy_mutation_performed"])

        status, baseline = dispatch_request("POST", "/v0/backtest", _backtest_payload())
        self.assertEqual(status, 200)
        status, cost = dispatch_request(
            "POST", "/v0/backtest", _backtest_payload(fee_bps=10.0, slippage_bps=10.0)
        )
        self.assertEqual(status, 200)
        status, comparison = dispatch_request(
            "POST",
            "/v0/compare",
            {
                "results": [
                    {"label": "baseline", "result": baseline},
                    {"label": "cost", "result": cost},
                ]
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(comparison["schema"], "qookey-crypto-toolkit-backtest-comparison-v0.2")
        self.assertFalse(comparison["selection_or_promotion_performed"])

        validation = {
            "schema": "qookey-crypto-toolkit-candle-validation-v0.2",
            "status": "PASS",
            "candle_count": 2,
            "gap_count": 0,
            "missing_bars": 0,
            "invalid_candle_count": 0,
        }
        status, report = dispatch_request(
            "POST",
            "/v0/report",
            {"title": "HTTP research check", "validation": validation},
        )
        self.assertEqual(status, 200)
        self.assertEqual(report["schema"], "qookey-crypto-toolkit-research-report-v0.2")
        self.assertIn("not a live-trading recommendation", report["markdown"])

    def test_openapi_lists_all_v02_routes(self) -> None:
        document = openapi_document()
        self.assertEqual(document["openapi"], "3.1.0")
        self.assertEqual(document["info"]["version"], "0.2.0")
        self.assertEqual(
            set(document["paths"]),
            {
                "/healthz",
                "/v0/capabilities",
                "/v0/validate",
                "/v0/indicators",
                "/v0/strategy",
                "/v0/risk",
                "/v0/backtest",
                "/v0/stress",
                "/v0/compare",
                "/v0/report",
            },
        )
        for path in set(document["paths"]) - {"/healthz", "/v0/capabilities"}:
            self.assertEqual(document["paths"][path]["post"]["security"], [{"bearerAuth": []}])

    def test_method_unknown_and_bad_payload_fail_closed(self) -> None:
        status, body = dispatch_request("GET", "/v0/risk")
        self.assertEqual(status, 405)
        self.assertEqual(body["error"]["code"], "METHOD_NOT_ALLOWED")
        self.assertTrue(all(value is False for value in body["authority"].values()))

        status, body = dispatch_request("POST", "/v0/validate", {"interval": "1h"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "INVALID_TOOL_INPUT")

        status, body = dispatch_request("GET", "/v0/does-not-exist")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
