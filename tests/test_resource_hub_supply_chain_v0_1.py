from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.toolkit.resource_hub_supply_chain import build_candidate_registry


POLICY_PATH = Path("config/resource_hub_supply_chain_v0_1.json")
SOURCE_COMMIT = "a" * 40


def _catalog() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "updated_at": "2026-09-15",
        "resources": [
            {
                "id": "anti-gambling-trader-tw",
                "name": "反詐投資王",
                "url": "https://github.com/mars-tw/anti-gambling-trader-tw",
                "categories": ["Finance / Crypto", "Data / Analytics"],
                "tags": ["trading-analysis", "backtesting", "risk-management"],
                "summary": "交易統計、回測與投資反詐研究工具。",
                "use_cases": ["檢查交易策略與風險"],
                "pricing": "open-source",
                "open_source": True,
                "license": "MIT",
                "status": "active",
            },
            {
                "id": "world-monitor",
                "name": "World Monitor",
                "url": "https://github.com/koala73/worldmonitor",
                "categories": ["OSINT / Intelligence", "Search / Research", "Data / Analytics"],
                "tags": ["geopolitics", "market", "news", "macro"],
                "summary": "全球市場與地緣政治情報研究儀表板。",
                "use_cases": ["研究宏觀與市場事件"],
                "pricing": "freemium",
                "open_source": True,
                "license": "AGPL-3.0-only",
                "status": "active",
            },
            {
                "id": "market-data-stack",
                "name": "Market Data Stack",
                "url": "https://example.com/market-data",
                "categories": ["Data / Analytics"],
                "tags": ["market-data", "ohlcv"],
                "summary": "Read-only OHLCV market data research toolkit.",
                "use_cases": ["historical price data research"],
                "pricing": "free",
                "open_source": True,
                "license": "MIT",
                "status": "active",
            },
            {
                "id": "lulu930128-github-profile",
                "name": "Lulu — AI Agent / Automation Projects",
                "url": "https://github.com/lulu930128",
                "categories": ["Data / Analytics"],
                "tags": ["automation", "market"],
                "summary": "General AI agent and automation projects for multiple markets.",
                "use_cases": ["automation experiments"],
                "pricing": "free",
                "open_source": None,
                "license": None,
                "status": "active",
            },
            {
                "id": "curated-design",
                "name": "Curated",
                "url": "https://curated.design/",
                "categories": ["Search / Research"],
                "tags": ["design", "portfolio"],
                "summary": "Curated design inspiration and portfolio references.",
                "use_cases": ["web design research"],
                "pricing": "freemium",
                "open_source": False,
                "license": None,
                "status": "active",
            },
            {
                "id": "openstreetmap",
                "name": "OpenStreetMap",
                "url": "https://www.openstreetmap.org/",
                "categories": ["Search / Research", "Data / Analytics"],
                "tags": ["maps", "gis", "geospatial"],
                "summary": "開放地圖資料。",
                "use_cases": ["地理資訊研究"],
                "pricing": "free",
                "open_source": None,
                "license": "ODbL-1.0",
                "status": "active",
            },
            {
                "id": "generic-llm",
                "name": "Generic LLM",
                "url": "https://example.com/llm",
                "categories": ["AI / LLM"],
                "tags": ["llm"],
                "summary": "Generic model endpoint.",
                "use_cases": [],
                "pricing": "freemium",
                "open_source": False,
                "license": None,
                "status": "active",
            },
        ],
    }


class ResourceHubSupplyChainV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_builds_read_only_candidates_with_exact_lineage(self) -> None:
        result = build_candidate_registry(_catalog(), self.policy, source_commit=SOURCE_COMMIT)

        self.assertEqual(result["schema"], "qookey-resource-hub-supply-chain-candidates-v0.1")
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertEqual(result["source"]["commit_sha"], SOURCE_COMMIT)
        self.assertEqual(result["source"]["repository"], "qookey109-pixel/ai-resource-hub")
        self.assertEqual(result["scanned_resource_count"], 7)
        self.assertEqual(result["policy"]["schema"], "qookey-resource-hub-supply-chain-policy-v0.1.1")

        ids = [item["resource_id"] for item in result["candidates"]]
        self.assertIn("anti-gambling-trader-tw", ids)
        self.assertIn("world-monitor", ids)
        self.assertIn("market-data-stack", ids)
        self.assertNotIn("lulu930128-github-profile", ids)
        self.assertNotIn("curated-design", ids)
        self.assertNotIn("openstreetmap", ids)
        self.assertNotIn("generic-llm", ids)

        anti = next(
            item for item in result["candidates"] if item["resource_id"] == "anti-gambling-trader-tw"
        )
        self.assertEqual(anti["integration_type"], "strategy_validation")
        self.assertEqual(anti["decision"], "REVIEW_REQUIRED")
        self.assertFalse(anti["automatic_install_authorized"])
        self.assertFalse(anti["automatic_execution_authorized"])
        self.assertFalse(anti["adapter_creation_authorized"])
        self.assertFalse(anti["live_trading_authorized"])

        world = next(item for item in result["candidates"] if item["resource_id"] == "world-monitor")
        self.assertEqual(world["integration_type"], "market_intelligence")
        self.assertIn("geopolit", world["strong_matched_signals"])
        self.assertGreaterEqual(world["relevance_score"], 35)

        market_data = next(
            item for item in result["candidates"] if item["resource_id"] == "market-data-stack"
        )
        self.assertIn("market", market_data["matched_signals"])
        self.assertNotIn("market", market_data["strong_matched_signals"])
        self.assertIn("market data", market_data["strong_matched_signals"])
        self.assertIn("ohlcv", market_data["strong_matched_signals"])

        authority = result["authority"]
        self.assertTrue(authority["workflow_dispatch_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "workflow_dispatch_only"
            )
        )

    def test_weak_signal_only_non_finance_resources_are_excluded(self) -> None:
        result = build_candidate_registry(_catalog(), self.policy, source_commit=SOURCE_COMMIT)
        ids = {item["resource_id"] for item in result["candidates"]}
        self.assertNotIn("lulu930128-github-profile", ids)
        self.assertNotIn("curated-design", ids)

    def test_rejects_unbound_source_commit(self) -> None:
        with self.assertRaisesRegex(ValueError, "source_commit"):
            build_candidate_registry(_catalog(), self.policy, source_commit="main")

    def test_fails_closed_if_automatic_execution_is_authorized(self) -> None:
        unsafe = deepcopy(self.policy)
        unsafe["safety"]["automatic_execution_authorized"] = True
        with self.assertRaisesRegex(ValueError, "safety boundary"):
            build_candidate_registry(_catalog(), unsafe, source_commit=SOURCE_COMMIT)

    def test_fails_closed_if_weak_signal_has_no_weight(self) -> None:
        invalid = deepcopy(self.policy)
        invalid["weak_domain_signals"].append("unweighted-signal")
        with self.assertRaisesRegex(ValueError, "missing weights"):
            build_candidate_registry(_catalog(), invalid, source_commit=SOURCE_COMMIT)


if __name__ == "__main__":
    unittest.main()
