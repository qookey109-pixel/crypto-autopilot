from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_CONFIG = ROOT / "config/qookey_crypto_toolkit_api_v0_2.json"
TOOLKIT_CONFIG = ROOT / "config/qookey_crypto_toolkit_v0_2.json"
EDGE = ROOT / "infra/cloudflare/qookey-toolkit-edge/src/index.js"
DOCKERFILE = ROOT / "infra/render/qookey-toolkit-api/Dockerfile"
SERVER = ROOT / "scripts/qookey_crypto_toolkit_http_v0_2.py"


class QookeyCryptoToolkitApiV02ConfigTests(unittest.TestCase):
    def test_api_contract_is_prepared_only_and_keeps_authority_closed(self) -> None:
        api = json.loads(API_CONFIG.read_text(encoding="utf-8"))
        toolkit = json.loads(TOOLKIT_CONFIG.read_text(encoding="utf-8"))

        self.assertEqual(api["schema"], "qookey-crypto-toolkit-api-v0.2")
        self.assertEqual(api["status"], "PREPARED_RESEARCH_ONLY")
        self.assertEqual(api["toolkit_version"], "0.2")
        self.assertFalse(api["deployment"]["automatic_deploy_authorized"])
        self.assertFalse(api["deployment"]["public_exposure_authorized"])
        self.assertTrue(all(value is False for value in api["safety_boundary"].values()))

        self.assertEqual(
            toolkit["interfaces"]["rest_api"],
            "IMPLEMENTED_PREPARED_RESEARCH_ONLY",
        )
        self.assertEqual(
            toolkit["interfaces"]["rest_api_config"],
            "config/qookey_crypto_toolkit_api_v0_2.json",
        )
        self.assertFalse(toolkit["cloud_execution"]["rest_api_deployment_authorized"])
        self.assertFalse(toolkit["cloud_execution"]["rest_api_public_exposure_authorized"])
        self.assertTrue(all(value is False for value in toolkit["safety_boundary"].values()))

    def test_route_contract_covers_all_eight_v02_tools(self) -> None:
        api = json.loads(API_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            set(api["origin"]["protected_routes"]),
            {
                "POST /v0/validate",
                "POST /v0/indicators",
                "POST /v0/strategy",
                "POST /v0/risk",
                "POST /v0/backtest",
                "POST /v0/stress",
                "POST /v0/compare",
                "POST /v0/report",
            },
        )
        self.assertEqual(
            set(api["origin"]["public_routes"]),
            {"GET /healthz", "GET /openapi.json", "GET /v0/capabilities"},
        )
        self.assertEqual(api["origin"]["max_request_bytes"], 2_000_000)
        self.assertTrue(api["origin"]["non_loopback_requires_bearer_token"])

    def test_edge_and_origin_are_thin_and_secret_safe(self) -> None:
        edge = EDGE.read_text(encoding="utf-8")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        server = SERVER.read_text(encoding="utf-8")

        self.assertIn('origin.startsWith("https://")', edge)
        self.assertIn("UPSTREAM_REDIRECT_BLOCKED", edge)
        self.assertIn('responseHeaders.delete("set-cookie")', edge)
        self.assertIn('responseHeaders.delete("location")', edge)
        for path in (
            "/v0/validate",
            "/v0/indicators",
            "/v0/strategy",
            "/v0/risk",
            "/v0/backtest",
            "/v0/stress",
            "/v0/compare",
            "/v0/report",
        ):
            self.assertIn(path, edge)

        self.assertNotIn("pip install", dockerfile)
        self.assertNotIn("R2_", dockerfile)
        self.assertNotIn("PIONEX_", dockerfile)
        self.assertNotIn("BINANCE_", dockerfile)
        self.assertIn("QOOKEY_TOOLKIT_API_TOKEN", server)
        self.assertIn("refusing non-loopback bind", server)
        self.assertNotIn("Authorization headers", server.split("log_message", 1)[-1])


if __name__ == "__main__":
    unittest.main()
